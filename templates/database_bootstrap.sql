\set ON_ERROR_STOP on
\getenv db BAIKOR_DATABASE
\getenv owner BAIKOR_OWNER
\getenv owner_password BAIKOR_OWNER_PASSWORD
\getenv writer BAIKOR_WRITER
\getenv writer_password BAIKOR_WRITER_PASSWORD
\getenv publisher BAIKOR_PUBLISHER
\getenv publisher_password BAIKOR_PUBLISHER_PASSWORD
\getenv publish BAIKOR_PUBLICATION_ENABLED

-- Operator-owned existing roles are preserved, including their passwords.
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', name, password)
FROM (VALUES (:'owner', :'owner_password'), (:'writer', :'writer_password'),
             (:'publisher', :'publisher_password')) AS requested(name, password)
WHERE name <> '' AND NOT EXISTS (SELECT FROM pg_roles WHERE rolname = requested.name)
\gexec

-- Refuse to use a privileged/group-member publication account.
\if :publish
SELECT CASE WHEN NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
                 AND NOT rolbypassrls AND NOT EXISTS
                 (SELECT FROM pg_auth_members WHERE member = r.oid)
            THEN 'true' ELSE 'false' END AS publisher_safe
FROM pg_roles r WHERE rolname = :'publisher'
\gset
\if :publisher_safe
\else
  \echo 'Publication role must be unprivileged and have no role memberships.'
  SELECT 1 / 0;
\endif
\endif

SELECT format('CREATE DATABASE %I OWNER %I', :'db', :'owner')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db')
\gexec
\connect :db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS baikor AUTHORIZATION :"owner";
GRANT CONNECT ON DATABASE :"db" TO :"writer";
GRANT USAGE ON SCHEMA baikor TO :"writer";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA baikor TO :"writer";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA baikor TO :"writer";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA baikor
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"writer";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA baikor
  GRANT USAGE, SELECT ON SEQUENCES TO :"writer";

-- No table-wide grant or inherited reader role for the GeoServer login.
\if :publish
GRANT CONNECT ON DATABASE :"db" TO :"publisher";
GRANT USAGE ON SCHEMA baikor TO :"publisher";
REVOKE ALL ON ALL TABLES IN SCHEMA baikor FROM :"publisher";
SELECT format('GRANT SELECT ON %I.%I TO %I', n.nspname, c.relname, :'publisher')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'baikor' AND c.relkind = 'v'
  AND c.relname IN ('public_construction_sites', 'public_construction_site_areas')
\gexec

-- Fail closed if PUBLIC or another grant exposes any application table.
SELECT CASE WHEN NOT EXISTS (
  SELECT FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'baikor' AND c.relkind IN ('r', 'p')
    AND has_table_privilege(:'publisher', c.oid, 'SELECT,INSERT,UPDATE,DELETE')
) THEN 'true' ELSE 'false' END AS publication_isolated
\gset
\if :publication_isolated
\else
  \echo 'Publication account has unexpected access to private tables.'
  SELECT 1 / 0;
\endif
\endif
