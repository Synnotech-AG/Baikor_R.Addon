"""Run the real bootstrap SQL against an isolated PostgreSQL/PostGIS container.

Requires Docker and a local PostGIS image (default: postgis/postgis:16-3.4).
No published ports or existing Kubernetes resources are used. Only the unique
container created by this run is removed, including its temporary data volume.
"""
import argparse
from pathlib import Path
import secrets
import subprocess
import time
import uuid


SQL = (Path(__file__).resolve().parents[1] / "templates/database_bootstrap.sql").read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="postgis/postgis:16-3.4")
    args = parser.parse_args()
    name = "baikor-owner-test-" + uuid.uuid4().hex
    password = secrets.token_urlsafe(32)
    roles = {"OWNER": "baikor_owner", "WRITER": "baikor_writer", "PUBLISHER": "baikor_publisher"}
    passwords = {key: secrets.token_urlsafe(32) for key in roles}
    container_id = None

    def sql(statement, *, user="postgres", database="baikor_test", bootstrap=False,
            publication=True, expect_error=None, publisher=None):
        login_password = password if user == "postgres" else passwords[
            next(key for key, value in roles.items() if value == user)]
        environment = dict(PGUSER=user, PGPASSWORD=login_password, PGDATABASE=database,
                           PGHOST="127.0.0.1", BAIKOR_DATABASE=database,
                           BAIKOR_PUBLICATION_ENABLED=str(publication).lower())
        for key, value in roles.items():
            if key == "PUBLISHER":
                value = (publisher or value) if publication else ""
            environment["BAIKOR_" + key] = value
            environment["BAIKOR_" + key + "_PASSWORD"] = passwords[key]
        command = ["docker", "exec", "-i"]
        for key, value in environment.items():
            command += ["-e", key + "=" + value]
        command += [container_id, "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1"]
        # Bootstrap starts in the maintenance DB; its script connects to the target.
        if bootstrap and user == "postgres":
            command += ["-d", "postgres"]
        result = subprocess.run(command, input=statement, text=True, capture_output=True, check=False)
        if expect_error:
            assert result.returncode != 0 and expect_error in result.stderr, (
                "Expected database permission failure: " + expect_error + "\n" + result.stderr)
        elif result.returncode:
            raise AssertionError("Database command failed:\n" + result.stderr)
        return result.stdout.strip()

    try:
        started = subprocess.run([
            "docker", "run", "--detach", "--rm", "--pull=never", "--network", "none",
            "--name", name, "-e", "POSTGRES_PASSWORD=" + password, args.image,
        ], text=True, capture_output=True, check=True)
        container_id = started.stdout.strip()
        for _ in range(60):
            ready = subprocess.run(["docker", "exec", container_id, "pg_isready", "-h", "127.0.0.1"],
                                   capture_output=True, check=False)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise AssertionError("Test PostgreSQL did not become ready in 60 seconds.")

        sql(SQL, bootstrap=True, publication=False)
        assert sql("SELECT count(*) FROM pg_extension WHERE extname = 'postgis';") == "1"
        assert sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database();") == "baikor_owner"
        assert sql("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = 'baikor';") == "baikor_owner"
        sql(SQL, user="baikor_owner", bootstrap=True, publication=False)
        assert sql("SELECT count(*) FROM pg_roles WHERE rolname = 'baikor_publisher';") == "0"
        # Enabling publication later needs the operator to create its missing login.
        sql(SQL, user="baikor_owner", bootstrap=True, expect_error="permission denied to create role")
        sql(SQL, bootstrap=True)
        assert sql("""SELECT count(*) FROM pg_roles WHERE rolname IN
                   ('baikor_owner', 'baikor_writer', 'baikor_publisher')
                   AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb
                   AND NOT rolcreaterole AND NOT rolbypassrls;""") == "3"
        print("PASS: first bootstrap creates database, PostGIS, schema and unprivileged logins.")

        sql("""CREATE TABLE baikor.private_test (id bigint GENERATED ALWAYS AS IDENTITY, value text);
            INSERT INTO baikor.private_test (value) VALUES ('retained');
            CREATE VIEW baikor.public_construction_sites AS SELECT id FROM baikor.private_test;
            CREATE VIEW baikor.public_construction_site_areas AS SELECT id FROM baikor.private_test;""",
            user="baikor_owner")
        for _ in range(2):
            sql(SQL, user="baikor_owner", bootstrap=True)
        assert sql("SELECT value FROM baikor.private_test;", user="baikor_writer") == "retained"
        sql("INSERT INTO baikor.private_test (value) VALUES ('writer');", user="baikor_writer")
        assert sql("SELECT count(*) FROM baikor.public_construction_sites;", user="baikor_publisher") == "2"
        sql("SELECT * FROM baikor.private_test;", user="baikor_publisher", expect_error="permission denied")
        sql("DELETE FROM baikor.private_test;", user="baikor_publisher", expect_error="permission denied")
        sql("CREATE TABLE baikor.denied (id int);", user="baikor_writer", expect_error="permission denied")
        print("PASS: owner reconciliation needs no server privileges; writer DML and publisher isolation hold.")

        sql("""CREATE TABLE baikor.after_migration (id bigserial, value text);
            DROP VIEW baikor.public_construction_sites;
            CREATE VIEW baikor.public_construction_sites AS SELECT id FROM baikor.private_test;""",
            user="baikor_owner")
        sql("INSERT INTO baikor.after_migration (value) VALUES ('default grants');", user="baikor_writer")
        sql("SELECT * FROM baikor.public_construction_sites;", user="baikor_publisher", expect_error="permission denied")
        sql(SQL, user="baikor_owner", bootstrap=True)
        assert sql("SELECT count(*) FROM baikor.public_construction_sites;", user="baikor_publisher") == "2"
        sql("SELECT * FROM baikor.after_migration;", user="baikor_publisher", expect_error="permission denied")
        assert sql("SELECT value FROM baikor.private_test ORDER BY id;", user="baikor_writer") == "retained\nwriter"
        print("PASS: later migrations inherit writer grants and owner reconciliation restores publication views.")

        sql(SQL, user="baikor_owner", bootstrap=True, publisher="missing_publisher", expect_error="permission denied to create role")
        sql("CREATE DATABASE without_postgis OWNER baikor_owner;", database="postgres")
        sql(SQL, user="baikor_owner", database="without_postgis", bootstrap=True,
            expect_error="permission denied to create extension")
        sql("CREATE DATABASE denied;", user="baikor_owner", expect_error="permission denied")
        assert sql("SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls FROM pg_roles WHERE rolname = current_user;",
                   user="baikor_owner") == "f"
        print("PASS: owner cannot create missing roles/databases or install PostGIS; no privilege elevation.")
    finally:
        if container_id:
            # IDs originate only from the successful unique docker run above.
            subprocess.run(["docker", "rm", "--force", "--volumes", container_id],
                           check=True, capture_output=True)


if __name__ == "__main__":
    main()
