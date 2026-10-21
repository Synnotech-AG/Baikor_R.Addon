# Baikor_R auf einem frischen Windows 11 Rechner installieren

Diese Anleitung richtet eine lokale Testumgebung mit Windows 11, Docker Desktop,
Ubuntu 24.04 unter WSL2, CIVITAS/CORE 1.6.0 und Baikor_R ein. Du führst alle
Schritte selbst aus. Vorhandene Dateien, Passwörter oder Cluster vom bisherigen
Entwicklungsrechner werden nicht benötigt.

Installiert werden PostgreSQL/PostGIS, Keycloak, das Core-Serviceportal und
Baikor_R. GeoServer, Masterportal, die öffentliche Geoportal-Veröffentlichung und
der optionale Import-Maschinenclient bleiben zunächst deaktiviert. Die Karte
innerhalb von Baikor_R funktioniert davon unabhängig.

Stand: 21. Oktober 2026. Die Anleitung verwendet bewusst feste Versionen:

Diese Fassung verwendet das Add-on `1.7.10` und die öffentlichen
App-/Chart-Pakete `1.7.9`.

| Bestandteil | Stand |
| --- | --- |
| CIVITAS/CORE | `v1.6.0`, plus die unten beschriebenen lokalen Anpassungen |
| Add-on | Release-Tag `1.7.10` |
| Öffentliches Baikor_R-Image | `ghcr.io/synnotech-ag/baikor-r:1.7.9` |
| Öffentliches Helm-Chart | `oci://ghcr.io/synnotech-ag/baikor-r-chart`, Version `1.7.9` |
| k3d / Kubernetes | `5.9.0` / `v1.35.4-k3s1` |
| Helm / kubectl | `3.20.0` / `1.35.4` |

Das Add-on legt die App- und Chart-Version fest. Beide Pakete werden von GHCR
heruntergeladen; ein GitHub-Login ist dafür nicht erforderlich. Die Anwendung
muss nicht lokal gebaut werden; .NET und Node.js werden auf dem Rechner nicht
benötigt.

Die Plattformanpassungen unten entsprechen den für Core 1.6 verwendeten
Komponenten unseres lokalen Tests. Die Anleitung wurde gegen die Quellen
geprüft; die Befehlsfolge wurde nicht erneut auf einem zweiten Windows-Rechner
ausgeführt.

## 1. Voraussetzungen

- Windows 11 auf einem Intel-/AMD-Rechner, Hardware-Virtualisierung aktiviert.
- Für diesen Test empfehle ich 32 GB RAM und mindestens 60 GB freien Speicher.
  Der Containerumgebung werden 16 GB RAM und vier CPUs zugewiesen.
- Administratorrechte für WSL und die Windows-Hosts-Datei.
- Internetzugriff auf GitHub/GHCR, GitLab, Docker Hub und die verwendeten
  Paket- und Chart-Repositories.
- Auf dem frischen Rechner dürfen die Ports 80, 443, 1883, 9876 und 6379 noch
  nicht durch andere Dienste belegt sein.

**Arbeitsweise:** Jeden Block vollständig ausführen und das Ergebnis prüfen.
Bei einem Fehler an dieser Stelle anhalten. Mit „Ubuntu“ ist immer das
Ubuntu-Terminal unter WSL gemeint, mit „PowerShell“ das Windows-Terminal.

## 2. WSL und Ubuntu installieren

**PowerShell als Administrator:**

```powershell
wsl --install -d Ubuntu-24.04
```

Windows neu starten, anschließend „Ubuntu 24.04“ aus dem Startmenü öffnen.
Einen Linux-Benutzernamen und ein Linux-Passwort anlegen. Dieses Passwort wird
später für `sudo` benötigt; es ist nicht das Baikor-Passwort.

**PowerShell:**

```powershell
wsl --update
wsl --set-version Ubuntu-24.04 2
wsl --list --verbose
notepad "$env:USERPROFILE\.wslconfig"
```

In der Datei folgende Einstellungen speichern. Falls sie bereits andere
Einstellungen enthält, diese erhalten und die Werte im vorhandenen Abschnitt
`[wsl2]` anpassen:

```ini
[wsl2]
memory=16GB
processors=4
swap=8GB
```

Ubuntu schließen, dann in PowerShell:

```powershell
wsl --shutdown
```

`wsl --list --verbose` muss für Ubuntu die Version `2` zeigen.
Siehe [Microsofts WSL-Installation](https://learn.microsoft.com/en-us/windows/wsl/install)
und [WSL-Konfiguration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).

## 3. Docker Desktop einrichten

[Docker Desktop für Windows installieren](https://docs.docker.com/desktop/setup/install/windows-install/)
und starten. In den Einstellungen:

1. **General → Use the WSL 2 based engine** aktivieren.
2. **Resources → WSL Integration → Ubuntu-24.04** aktivieren.
3. **Start Docker Desktop when you sign in** aktivieren.
4. Das eingebaute Kubernetes von Docker Desktop ausgeschaltet lassen. Unser
   Kubernetes wird mit k3d angelegt.
5. Änderungen mit **Apply & restart** übernehmen.

Jetzt Ubuntu öffnen und prüfen:

```bash
docker version
docker run --rm hello-world
```

Erwartet: Docker zeigt Client **und Server**, danach erscheint die
Hello-World-Erfolgsmeldung. Docker Engine nicht zusätzlich über `apt` in Ubuntu
installieren. Die [Docker-WSL-Anleitung](https://docs.docker.com/desktop/features/wsl/)
beschreibt diese Integration.

## 4. Arbeitsverzeichnis und Werkzeuge vorbereiten

Ab hier alle Bash-Blöcke in **Ubuntu** ausführen. Die Dateien bleiben im
Linux-Dateisystem, nicht unter `/mnt/c`.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3 python3-venv \
  python3-pip openssl gettext-base dos2unix jq unzip

umask 077
export LAB="$HOME/baikor-lab"
mkdir -p "$LAB/downloads" "$LAB/kube"
cd "$LAB/downloads"
```

Werkzeuge herunterladen und Prüfsummen prüfen:

```bash
(
set -e
curl -fL -o kubectl https://dl.k8s.io/release/v1.35.4/bin/linux/amd64/kubectl
curl -fL -o kubectl.sha256 https://dl.k8s.io/release/v1.35.4/bin/linux/amd64/kubectl.sha256
printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum --check
sudo install -m 0755 kubectl /usr/local/bin/kubectl

curl -fLO https://get.helm.sh/helm-v3.20.0-linux-amd64.tar.gz
curl -fLO https://get.helm.sh/helm-v3.20.0-linux-amd64.tar.gz.sha256sum
sha256sum --check helm-v3.20.0-linux-amd64.tar.gz.sha256sum
tar -xzf helm-v3.20.0-linux-amd64.tar.gz
sudo install -m 0755 linux-amd64/helm /usr/local/bin/helm

curl -fLO https://github.com/k3d-io/k3d/releases/download/v5.9.0/k3d-linux-amd64
curl -fLO https://github.com/k3d-io/k3d/releases/download/v5.9.0/checksums.txt
sha256sum --check --ignore-missing checksums.txt
sudo install -m 0755 k3d-linux-amd64 /usr/local/bin/k3d

kubectl version --client
helm version --short
k3d version
)
```

Erwartete Versionen: kubectl `v1.35.4`, Helm `v3.20.0`, k3d `v5.9.0`.
Bei einer fehlgeschlagenen Prüfsumme das betroffene Programm nicht installieren.

## 5. Core und Add-on herunterladen

**Ubuntu:**

```bash
cd "$LAB"
git clone https://gitlab.com/civitas-connect/civitas-core/civitas-core-v1/civitas-core.git core
cd "$LAB/core"
git checkout --detach v1.6.0
git rev-parse HEAD

git submodule add https://github.com/Synnotech-AG/Baikor_R.Addon.git \
  core_platform/addons/baikor_r_addon
git -C core_platform/addons/baikor_r_addon checkout --detach \
  1.7.10
git -C core_platform/addons/baikor_r_addon describe --tags --exact-match

python3 -m venv "$LAB/.venv"
source "$LAB/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ansible-galaxy collection install -r ansible-collections.yml
```

Der Core-Commit muss `86e69334800ce96bb2731782d2c1a9de9c5a9e91` sein,
der Add-on-Tag muss `1.7.10` lauten.
Core selbst liegt weiterhin bei seinem Anbieter auf GitLab; Baikor_R und das
Add-on liegen auf GitHub.

Eine Datei für alle weiteren Terminal-Sitzungen anlegen:

```bash
cat > "$LAB/env.sh" <<'SH'
export LAB="$HOME/baikor-lab"
export CORE_DIR="$LAB/core"
export KUBECONFIG="$LAB/kube/config"
export KUBECONTEXT="k3d-civitas-local-baikor"
export ANSIBLE_CONFIG="$CORE_DIR/ansible.cfg"
export DOMAIN="civitas.test"
export CLUSTER_IP="127.0.0.1"
umask 077
source "$LAB/.venv/bin/activate"
SH

source "$LAB/env.sh"
ansible --version
```

Ansible muss `core 2.18.6` ausgeben. **Nach jedem neu geöffneten Ubuntu-Terminal
zuerst `source ~/baikor-lab/env.sh` ausführen.**

## 6. Core 1.6 für den lokalen Test vorbereiten

Core 1.6.0 benötigt in diesem Testprofil eine schmale Keycloak-Korrektur und
den passenden Serviceportal-Imagepfad. Außerdem werden die Infrastruktur-Charts
fest gepinnt. Diese Änderungen betreffen deinen lokalen Core-Checkout.

**Ubuntu:**

```bash
cd "$CORE_DIR"
git fetch origin 8b6d335fb881b323c79b7c5bdec2cde2b1c78c0c
git show --format= 8b6d335fb881b323c79b7c5bdec2cde2b1c78c0c \
  -- core_platform/tasks/access/keycloak/idm-config/keycloak_5_clients.yml \
  > "$LAB/core-keycloak.patch"
git apply --check "$LAB/core-keycloak.patch"
git apply "$LAB/core-keycloak.patch"

python - <<'PY'
import os
from pathlib import Path
import yaml

core = Path(os.environ['CORE_DIR'])
p = core / 'core_platform/vars/software_references.yml'
doc = yaml.safe_load(p.read_text())
portal = doc['software']['stack_access']['service_portal']
portal['repository'] = 'civitas-connect/civitas-core/civitas-core-v1/civitas-core-portal'
portal['tag'] = '2.0.0@sha256:9253514e3849c34b342887087911719ecde9b7a6378fc49cebd2f39ce33fb95d'
p.write_text(yaml.safe_dump(doc, sort_keys=False))

p = core / 'local_deployment/startup.sh'
text = p.read_text()
for old, new in [
    (' ingress-nginx ingress-nginx/ingress-nginx\n',
     ' ingress-nginx ingress-nginx/ingress-nginx --version 4.15.1\n'),
    (' metallb metallb/metallb\n',
     ' metallb metallb/metallb --version 0.16.1\n'),
]:
    assert text.count(old) == 1, 'Unerwarteter Stand von startup.sh'
    text = text.replace(old, new)
p.write_text(text)
print('Core-Anpassungen vorbereitet.')
PY
```

Diesen Vorbereitungsschritt nur einmal ausführen. Ein erneutes `git apply`
würde melden, dass der Patch bereits angewendet ist.

## 7. Kubernetes und lokale Zertifizierungsstelle erstellen

**Ubuntu:**

```bash
cat > "$LAB/cluster.yml" <<'YAML'
apiVersion: k3d.io/v1alpha5
kind: Simple
metadata:
  name: civitas-local-baikor
image: rancher/k3s:v1.35.4-k3s1
servers: 1
agents: 2
kubeAPI:
  host: localhost
ports:
  - port: 80:80
    nodeFilters: [loadbalancer]
  - port: 443:443
    nodeFilters: [loadbalancer]
  - port: 1883:1883
    nodeFilters: [loadbalancer]
  - port: 9876:9876
    nodeFilters: [loadbalancer]
  - port: 6379:6379
    nodeFilters: [loadbalancer]
options:
  k3d:
    wait: true
    timeout: 180s
  k3s:
    extraArgs:
      - arg: --disable=traefik
        nodeFilters: ["server:*"]
  kubeconfig:
    updateDefaultKubeconfig: false
    switchCurrentContext: false
YAML

k3d cluster create --config "$LAB/cluster.yml"
k3d kubeconfig get civitas-local-baikor > "$KUBECONFIG"
chmod 600 "$KUBECONFIG"
kubectl config current-context
kubectl wait --for=condition=Ready nodes --all --timeout=600s

cd "$CORE_DIR"
bash local_deployment/startup.sh -c
kubectl wait --for=condition=Ready clusterissuer/selfsigned-ca --timeout=180s
kubectl get nodes
```

Erwartet: Kontext `k3d-civitas-local-baikor`, drei Nodes mit Status `Ready` und
ein bereiter ClusterIssuer. `startup.sh` installiert Ingress-NGINX, MetalLB und
cert-manager sowie die lokale Zertifizierungsstelle.

**Nicht zusätzlich `startup.sh -k` ausführen:** Der Cluster wurde bereits
angelegt. Auch `-c` später nicht erneut ausführen, denn es erzeugt neue CA-Schlüssel.

## 8. Namen und Zertifikatsvertrauen einrichten

**Ubuntu:**

```bash
printf '\n127.0.0.1 civitas.test idm.civitas.test baikor-r.civitas.test\n' \
  | sudo tee -a /etc/hosts
sudo install -m 0644 "$CORE_DIR/local_deployment/.ssl/civitas.crt" \
  /usr/local/share/ca-certificates/baikor-lab.crt
sudo update-ca-certificates
getent hosts idm.civitas.test
```

**PowerShell als Administrator:**

```powershell
Add-Content -LiteralPath "$env:WINDIR\System32\drivers\etc\hosts" `
  -Value "`r`n127.0.0.1 civitas.test idm.civitas.test baikor-r.civitas.test"
ipconfig /flushdns
```

Anschließend **PowerShell unter deinem normalen Windows-Benutzer** öffnen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc 'cat "$HOME/baikor-lab/core/local_deployment/.ssl/civitas.crt"' |
  Set-Content -Encoding ascii -LiteralPath "$env:TEMP\baikor-lab-ca.crt"
Import-Certificate -FilePath "$env:TEMP\baikor-lab-ca.crt" `
  -CertStoreLocation Cert:\CurrentUser\Root
```

Falls Windows nachfragt, den Import dieser gerade selbst erzeugten lokalen CA
bestätigen. Edge/Chrome danach vollständig schließen und neu öffnen.

Die private Datei `civitas.key` bleibt in Ubuntu. Nur die öffentliche `.crt`-Datei
wird nach Windows übernommen.

## 9. Persönliche Core-Konfiguration erstellen

Der folgende Block übernimmt die offizielle lokale Core-Vorlage und trägt die
konkreten Pfade sowie ein von dir gewähltes Passwort ein. Die Datei liegt außerhalb
der Git-Repositories und ist nur für deinen Linux-Benutzer lesbar.

**Ubuntu:**

```bash
source "$HOME/baikor-lab/env.sh"
cd "$CORE_DIR"
python - <<'PY'
import getpass
import os
import secrets
import string
import subprocess
from pathlib import Path
import yaml

lab = Path(os.environ['LAB'])
core = Path(os.environ['CORE_DIR'])
target = lab / 'inventory.yml'
assert not target.exists(), 'inventory.yml existiert bereits; nicht neu erzeugen.'
password = getpass.getpass('Neues Core-Admin-Passwort (mindestens 16 Zeichen): ')
confirmation = getpass.getpass('Passwort wiederholen: ')
allowed = set(string.ascii_letters + string.digits + '!@#%_+-')
assert password == confirmation, 'Passwoerter sind unterschiedlich.'
assert len(password) >= 16 and set(password) <= allowed, 'Laenge oder Zeichen ungueltig.'
assert all((any(c.islower() for c in password), any(c.isupper() for c in password),
            any(c.isdigit() for c in password), any(c in '!@#%_+-' for c in password))), \
    'Kleinbuchstabe, Grossbuchstabe, Ziffer und Sonderzeichen sind erforderlich.'

template = subprocess.check_output(
    ['git', '-C', str(core), 'show', 'v1.6.0:inventory_loc_k3d.yml'], text=True)
doc = yaml.safe_load(template)
v = doc['all']['children']['controller']['vars']

# Auch Beispielpasswoerter derzeit ausgeschalteter Komponenten ersetzen.
secret_keys = {'password', 'default_password', 'master_password', 'jwt_secret',
               'admin_user_password', 'redis_auth_password', 'db_secret'}
def refresh(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in secret_keys and isinstance(child, str):
                value[key] = secrets.token_urlsafe(36) + '!Aa1'
            else:
                refresh(child)
    elif isinstance(value, list):
        for child in value:
            refresh(child)
refresh(v)

v['inv_k8s']['config']['context'] = os.environ['KUBECONTEXT']
v['inv_k8s']['ingress']['ca_path'] = str(core / 'local_deployment/.ssl/civitas.crt')
v['inv_k8s']['podSecurityAdmission'] = {'enable': False}
v['inv_access']['platform']['master_password'] = password
v['inv_access']['tenant'] = {'tenant_password': password}
certs = v['inv_access']['service_portal']['certs']
for key, name in [('civitas_crt', 'civitas.crt'), ('civitas_crl', 'civitas.crl'),
                  ('civitas_crl_pem', 'civitas.crl.pem')]:
    certs[key] = str(core / 'local_deployment/.ssl' / name)
v['inv_addons'] = {'import': False, 'addons': ['addons/baikor_r_addon/tasks.yml']}
target.write_text(yaml.safe_dump(doc, sort_keys=False))
target.chmod(0o600)
(lab / 'no-log.yml').write_text('ansible_debug:\n  no_log: true\n')
print('Private inventory.yml erstellt; Passwort nicht ausgegeben.')
PY
```

Erlaubte Sonderzeichen für dieses lokale Core-Passwort: `! @ # % _ + -`.
Das Passwort in deinem Passwortmanager aufbewahren. Nicht die komplette
Inventory in Chats oder Tickets kopieren; sie enthält Zugangsdaten.

## 10. Core installieren

Die Core-Basisinstallation behält den Core-1.6-Standard
`podSecurityAdmission.enable: false`: Nicht alle Core-Komponenten unterstützen
`restricted` ohne weitere Anpassungen. Schritt 13 aktiviert die Einstellung vor
dem reinen Add-on-Lauf, damit dessen Namespace mit `restricted` angelegt wird.

**Ubuntu:**

```bash
cd "$CORE_DIR"
ansible-playbook -i "$LAB/inventory.yml" core_platform/playbook.yml \
  -e "K8S_KUBECONFIG_PATH=$LAB/kube" -e "@$LAB/no-log.yml" \
  --tags all --skip-tags addons

kubectl -n tst-database-stack get pods,pvc
kubectl -n tst-access-stack get pods,ingress
curl --fail --show-error --silent \
  https://idm.civitas.test/realms/tst/.well-known/openid-configuration \
  | python -m json.tool
```

Der Playbook-Lauf muss mit `failed=0` und `unreachable=0` abschließen. Der erste
Lauf lädt viele Images und kann einige Zeit dauern. Der `curl`-Aufruf muss die
OIDC-Konfiguration als JSON liefern, ohne Zertifikatswarnung und ohne `-k`.

Im Windows-Browser öffnen:

- Core-Serviceportal: <https://civitas.test>
- Keycloak-Verwaltung: <https://idm.civitas.test/admin/>

Keycloak-Login: `admin@civitas.test` und dein Passwort aus Schritt 9. Der
Tenant-Realm heißt `tst`. Die Baikor-Anwendung wird im nächsten Schritt ergänzt.

## 11. PostgreSQL für das Add-on bereitstellen

Core hat bereits den PostgreSQL-Server angelegt. Jetzt erhält dieser ein
Serverzertifikat. In einem frei gewählten Namespace werden die CA und eine
Kopie des Bootstrap-Admin-Zugangs bereitgestellt. **Die Baikor-Datenbank und
die Baikor-Rollen werden hier noch nicht angelegt.**

**Ubuntu:**

```bash
kubectl create namespace baikor-database-access
kubectl label namespace baikor-database-access \
  pod-security.kubernetes.io/enforce=restricted

kubectl apply -f - <<'YAML'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: central-db-tls
  namespace: tst-database-stack
spec:
  secretName: central-db-tls
  issuerRef:
    name: selfsigned-ca
    kind: ClusterIssuer
  dnsNames:
    - central-db
    - central-db.tst-database-stack
    - central-db.tst-database-stack.svc
    - central-db.tst-database-stack.svc.cluster.local
YAML

kubectl -n tst-database-stack wait --for=condition=Ready \
  certificate/central-db-tls --timeout=180s
kubectl -n tst-database-stack patch postgresql central-db --type=merge \
  -p '{"spec":{"tls":{"secretName":"central-db-tls"}}}'

python - <<'PY'
import base64
import json
import os
import subprocess
import time
from pathlib import Path

def kjson(*args):
    return json.loads(subprocess.check_output(['kubectl', *args, '-o', 'json'], text=True))

admin = kjson('-n', 'tst-database-stack', 'get', 'secret',
              'postgres.central-db.credentials.postgresql.acid.zalan.do')['data']
ca = Path(os.environ['CORE_DIR']) / 'local_deployment/.ssl/civitas.crt'
for name, data in [
    ('bootstrap-admin', {key: admin[key] for key in ['username', 'password']}),
    ('central-db-tls', {'ca.crt': base64.b64encode(ca.read_bytes()).decode()}),
]:
    doc = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
           'metadata': {'name': name, 'namespace': 'baikor-database-access'}, 'data': data}
    result = subprocess.run(['kubectl', 'create', '-f', '-'], input=json.dumps(doc),
                            text=True, capture_output=True)
    assert result.returncode == 0, 'Secret-Erstellung fehlgeschlagen: ' + name

deadline = time.monotonic() + 600
while time.monotonic() < deadline:
    pods = kjson('-n', 'tst-database-stack', 'get', 'pods',
                 '-l', 'cluster-name=central-db')['items']
    ready = len(pods) == 2 and all(
        not p['metadata'].get('deletionTimestamp') and
        any(c['type'] == 'Ready' and c['status'] == 'True'
            for c in p['status'].get('conditions', [])) and
        any(v.get('secret', {}).get('secretName') == 'central-db-tls'
            for v in p['spec'].get('volumes', []))
        for p in pods)
    if ready:
        print('Beide PostgreSQL-Pods bereit; TLS-Secret eingebunden.')
        break
    time.sleep(5)
else:
    raise SystemExit('PostgreSQL-TLS-Rollout nach 600 Sekunden nicht bereit.')
PY
```

Der verwendete lokale Core-Postgres-Admin kann Datenbank und Rollen anlegen sowie
PostGIS aktivieren. Das Add-on benötigt beim ersten Lauf diese Möglichkeiten.
Die PostGIS-Binaries sind im vom Core verwendeten PostgreSQL-Image vorhanden.
Schritt 15 ersetzt diesen privilegierten Zugang für weitere Add-on-Deployments.

## 12. Öffentliche Baikor-Pakete abrufen

**Ubuntu:**

```bash
docker pull ghcr.io/synnotech-ag/baikor-r:1.7.9
helm show chart oci://ghcr.io/synnotech-ag/baikor-r-chart --version 1.7.9
helm pull oci://ghcr.io/synnotech-ag/baikor-r-chart --version 1.7.9 \
  --destination "$LAB/downloads"
```

Alle drei Befehle müssen erfolgreich sein. In der Chart-Ausgabe müssen `version`
und `appVersion` jeweils `1.7.9` lauten; das Chart liegt anschließend als
`$LAB/downloads/baikor-r-chart-1.7.9.tgz` vor. Beide Pakete müssen ohne
Registry-Login abrufbar sein. Bei einem Fehler hier anhalten und die
Veröffentlichung sowie den GHCR-Zugriff prüfen.

Die Kubernetes-Nodes laden das Image beim Deployment selbst von GHCR.
Anwendung und Datenbank-Migrationsjob verwenden dasselbe öffentliche Image.

## 13. Add-on konfigurieren und installieren

**Ubuntu:**

```bash
python - <<'PY'
import os
from pathlib import Path
import yaml

p = Path(os.environ['LAB']) / 'inventory.yml'
doc = yaml.safe_load(p.read_text())
v = doc['all']['children']['controller']['vars']
v['inv_k8s']['podSecurityAdmission'] = {'enable': True}
v['inv_addons'] = {
    'import': True,
    'addons': ['addons/baikor_r_addon/tasks.yml'],
    'baikor_r': {
        'enable': True,
        'enable_ingress': True,
        'enable_gateway': False,
        'ns_create': True,
        'ns_name': 'tst-baikor-r-stack',
        'subdomain': 'baikor-r',
        'authentication': {
            'allow_invalid_server_certificate': False,
            'assign_platform_admin_roles': True,
        },
        'image_registry': {'inherit_core': False},
        'bootstrap_image_registry': {'inherit_core': False},
        'imports': {'service_account': {'enable': False}},
        'publication': {'enable': False, 'masterportal': {'enable': False}},
        'database': {
            'namespace': 'baikor-database-access',
            'host': 'central-db.tst-database-stack.svc.cluster.local',
            'port': 5432,
            'name': 'baikor_r',
            'application_secret': 'baikor-writer',
            'migration_secret': 'baikor-owner',
            'ca_secret': 'central-db-tls',
            'ssl_mode': 'VerifyFull',
            'trust_server_certificate': False,
            'local_provision': {'enable': False},
            'bootstrap': {
                'enable': True,
                'admin_secret': 'bootstrap-admin',
                'generate_credentials': True,
                'maintenance_database': 'postgres',
                'application_username': 'baikor_r_writer',
                'migration_username': 'baikor_r_owner',
            },
        },
    },
}
p.write_text(yaml.safe_dump(doc, sort_keys=False))
print('Add-on-Konfiguration gespeichert.')
PY

cd "$CORE_DIR"
ansible-playbook -i "$LAB/inventory.yml" core_platform/playbook.yml \
  -e "K8S_KUBECONFIG_PATH=$LAB/kube" -e "@$LAB/no-log.yml" --tags addons
```

`assign_platform_admin_roles: true` ist hier ein bewusster Komfortschalter für
deinen lokalen Test. Er gibt dem vorhandenen Core-Admin die Baikor-Rollen. Im
Produktionsbetrieb werden Rollen gezielt in Keycloak zugewiesen.

Der Lauf legt die Datenbank und Owner-/Writer-Rollen an, aktiviert PostGIS,
führt die Schema-Migrationen aus und installiert die Anwendung. Ihren Namespace
legt das Add-on über das Core-Template mit `restricted` Pod Security an.
Mit dieser Inventory weitere Deployments auf `--tags addons` begrenzen. Vor
einem vollständigen Core-Lauf müssen die Core-Komponenten für `restricted`
vorbereitet oder die Einstellung für diesen Basislauf wieder auf `false`
gesetzt werden. Die bereits vorhandenen Add-on-Namespace-Labels bleiben erhalten.

Die Add-on-Pins wählen App und Chart `1.7.9`. Durch `inherit_core: false` werden
die öffentlichen Paketquellen direkt verwendet. Ein Image-Override in
`helm_values` ist für diese Installation nicht erforderlich.

## 14. Installation und Anwendung prüfen

**Ubuntu:**

```bash
kubectl -n tst-baikor-r-stack rollout status deployment/baikor-r --timeout=600s
kubectl -n tst-baikor-r-stack wait --for=condition=Ready \
  certificate/baikor-r-tls --timeout=180s
kubectl -n tst-baikor-r-stack get pods,jobs,pvc,ingress
kubectl get namespace tst-baikor-r-stack \
  -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}{"\n"}'
curl --fail --show-error --silent https://baikor-r.civitas.test/health/ready
```

Erwartet: App-Pod bereit, abgeschlossener Migrationsjob (sofern noch nicht
automatisch bereinigt), PVCs `Bound`, Namespace-Ausgabe `restricted` und
erfolgreiche Readiness-Antwort (`Healthy`). Die Readiness prüft die DB-Verbindung.

Prüfen, dass der API-Server einen unzulässigen Pod tatsächlich zurückweist:

```bash
kubectl -n tst-baikor-r-stack run psa-rejection-check \
  --image=busybox:1.36 --restart=Never --dry-run=server --command -- true
```

**Hier ist eine Ablehnung mit `violates PodSecurity ... restricted` das erwartete
Ergebnis.** Der Befehl erstellt keinen Pod. Eine erfolgreiche Pod-Annahme wäre
ein Fehler und sollte vor weiteren Tests untersucht werden.

Im Windows-Browser <https://baikor-r.civitas.test> öffnen und mit
`admin@civitas.test` und deinem Passwort aus Schritt 9 anmelden. Einen eventuell
verlangten initialen Passwortwechsel durchführen und das neue Passwort merken.

Anschließend in der Oberfläche:

1. Eine Baustelle mit eindeutigem Namen anlegen, zum Beispiel
   `Installationstest 2026-10-21`. Die angezeigten Pflichtfelder ausfüllen und
   eine Fläche in der Karte zeichnen.
2. Speichern, zur Übersicht wechseln und die Baustelle erneut öffnen.
3. Titel und einen weiteren Wert ändern, speichern und die Seite neu laden.
4. Eine kleine Testdatei anhängen, herunterladen und den Inhalt vergleichen.
5. Abmelden und wieder anmelden. Baustelle, Änderungen und Anhang müssen weiter
   vorhanden sein.
6. Eine zweite Wegwerf-Baustelle anlegen und löschen. Die erste für den
   Neustarttest behalten.

Damit werden Anmeldung, Berechtigungen, Geometrie, DB-Persistenz und
Dateispeicherung geprüft. Es ist keine vollständige fachliche Abnahme.

## 15. Auf den Owner-Zugang für weitere Deployments wechseln

Dieser Schritt gehört zur Installation. Das Add-on soll seinen nächsten Lauf
mit dem begrenzten Datenbank-Owner ausführen können.

**Ubuntu:**

```bash
python - <<'PY'
import os
from pathlib import Path
import yaml

p = Path(os.environ['LAB']) / 'inventory.yml'
doc = yaml.safe_load(p.read_text())
bootstrap = doc['all']['children']['controller']['vars']['inv_addons']['baikor_r']['database']['bootstrap']
bootstrap.update({
    'admin_secret': 'baikor-owner',
    'maintenance_database': 'baikor_r',
    'generate_credentials': False,
})
p.write_text(yaml.safe_dump(doc, sort_keys=False))
print('Weitere Deployments verwenden den Owner-Zugang.')
PY

cd "$CORE_DIR"
ansible-playbook -i "$LAB/inventory.yml" core_platform/playbook.yml \
  -e "K8S_KUBECONFIG_PATH=$LAB/kube" -e "@$LAB/no-log.yml" --tags addons
curl --fail --show-error --silent https://baikor-r.civitas.test/health/ready
```

Erst wenn dieser Lauf erfolgreich war und die Testbaustelle weiter vorhanden
ist, die eigens erstellte Bootstrap-Secret-Kopie entfernen:

```bash
kubectl -n baikor-database-access delete secret bootstrap-admin
```

`baikor-owner`, `baikor-writer`, die CA und die ursprünglichen Core-Secrets
bleiben erhalten. `bootstrap.enable` bleibt `true`: Die eingeschränkten
Grant-Abgleiche gehören auch zu späteren Deployments. Die laufende App verwendet
weiterhin den Writer; nur Bootstrap und Migrationen verwenden den Owner.

## 16. Neustart und Weiterbetrieb testen

Vor dem Neustart in Ubuntu die vorhandenen Datenträger erfassen:

```bash
kubectl get pvc -A -o json > "$LAB/pvc-before-restart.json"
k3d cluster stop civitas-local-baikor
```

Windows neu starten, anmelden und warten, bis Docker Desktop läuft.
**Ubuntu öffnen:**

```bash
source "$HOME/baikor-lab/env.sh"
docker version
k3d cluster start civitas-local-baikor
kubectl wait --for=condition=Ready nodes --all --timeout=600s
kubectl -n tst-access-stack rollout status statefulset/idmkeycloak --timeout=600s
kubectl -n tst-baikor-r-stack rollout status deployment/baikor-r --timeout=600s
curl --fail --show-error --silent --retry 30 --retry-all-errors --retry-delay 5 \
  https://baikor-r.civitas.test/health/ready

python - <<'PY'
import json
import os
import subprocess
from pathlib import Path

before = json.loads((Path(os.environ['LAB']) / 'pvc-before-restart.json').read_text())
after = json.loads(subprocess.check_output(['kubectl', 'get', 'pvc', '-A', '-o', 'json']))
def identities(doc):
    return {(p['metadata']['namespace'], p['metadata']['name']):
            (p['metadata']['uid'], p['spec'].get('volumeName')) for p in doc['items']}
assert identities(before) == identities(after), 'PVCs haben sich unerwartet geaendert.'
print('Alle PVCs und Volume-Zuordnungen unveraendert.')
PY
```

Im Browser erneut anmelden. Die erste Testbaustelle, ihre gezeichnete Fläche,
die Änderungen und der herunterladbare Anhang müssen erhalten sein. Es darf
kein erneutes Zuweisen von Rollen und kein erneutes Deployment nötig sein.

Der Test oben umfasst einen geregelten Cluster-Stopp mit Windows-Neustart.
Für den normalen Rechner-Neustart anschließend Windows noch einmal neu starten,
ohne zuvor `k3d cluster stop` auszuführen. Nach dem Start von Docker Desktop
dieselben Prüfungen wiederholen; `k3d cluster start civitas-local-baikor` kann
zum expliziten Start verwendet werden.

Zum späteren Arbeiten genügen normalerweise:

```bash
source "$HOME/baikor-lab/env.sh"
k3d cluster start civitas-local-baikor
```

Zum Beenden ohne Datenverlust:

```bash
k3d cluster stop civitas-local-baikor
```

`cluster delete`, ein Docker-Factory-Reset und das Löschen von Docker-Volumes
gehören nicht zum normalen Start/Stopp. Diese lokale Umgebung ersetzt kein Backup.

## 17. Bei Problemen

| Beobachtung | Zuerst prüfen |
| --- | --- |
| `docker version` zeigt keinen Server | Docker Desktop gestartet und Ubuntu-Integration aktiviert? |
| Installation scheitert beim Port-Binding | Läuft bereits ein Dienst oder Cluster auf einem der Ports aus Schritt 1? |
| Zertifikatsfehler im Browser | Schritt 8 im selben Windows-Benutzer ausgeführt und Browser neu gestartet? |
| Zertifikatsfehler in Ansible | `source ~/baikor-lab/env.sh`, CA-Pfad in Inventory und Zertifikate aus Schritt 8 prüfen. |
| `ErrImagePull` / `ImagePullBackOff` | Öffentlichen Abruf aus Schritt 12, GHCR-Zugriff der Kubernetes-Nodes und Image-Tag `1.7.9` prüfen. |
| `Kein Zugriff` nach Anmeldung | In Keycloak Realm `tst` wählen, Benutzer öffnen, unter Role mapping die Client-Rolle `baikor-r / baikor_admin` prüfen. Danach abmelden und neu anmelden. |
| `Pending` / `CrashLoopBackOff` | Ressourcen, PVCs und Events prüfen; nicht die Datenbank oder Secrets neu anlegen. |
| Deployment bleibt bei Bootstrap/Migration stehen | Den fehlgeschlagenen Job und seine Events prüfen. Erst Ursache beheben, dann denselben Add-on-Lauf wiederholen. |

Nützliche Diagnosebefehle in Ubuntu:

```bash
source "$HOME/baikor-lab/env.sh"
kubectl get nodes
kubectl get pods -A
kubectl -n tst-baikor-r-stack get events --sort-by=.lastTimestamp
kubectl -n baikor-database-access get jobs,pods
kubectl -n tst-database-stack get pods,pvc
```

Für eine Rückfrage reichen zunächst der fehlgeschlagene Schritt, der Task-Name
und die Fehlermeldung ohne Zugangsdaten. Keine Secret-Inhalte oder vollständige
Inventory veröffentlichen. Zertifikatsprüfungen nicht als Fehlerbehebung abschalten.

## Was danach optional folgt

Für eine Geoportal-Veröffentlichung müssen zusätzlich Core-GeoServer und
Masterportal aktiviert werden. Das getestete Core-1.6-Profil benötigt eine
operatorseitige JNDI-Datenquelle mit Publisher-Zugang und TLS-Prüfung. Anschließend
werden die vom Add-on bereitgestellten Layer in die gemeinsame Masterportal-
Konfiguration übernommen. `publication.enable: true` allein erledigt diese
Betreiberaufgaben nicht. Die vorliegende Anleitung schließt diesen zusätzlichen
Integrationsschritt ausdrücklich nicht ein.

Für den produktiven Betrieb gelten außerdem die Betreiberangaben im
[Add-on-README](https://github.com/Synnotech-AG/Baikor_R.Addon/blob/1.7.10/README.md).
