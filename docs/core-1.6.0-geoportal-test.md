# Lokaler Geoportal-Test mit Core 1.6.0

Stand: 16.10.2026. **Lokaler Test abgeschlossen: App, Datenbank,
GeoServer-Publikation, Statuswechsel und Portal-Oberfläche erfolgreich geprüft.**
Die Publikation verwendet eine zusätzliche JNDI-Datenquelle des Betreibers;
der direkte Datastore mit dem enthaltenen GeoTools 34.0 bleibt blockiert.

Dieser Folgetest verwendet die frische lokale Umgebung
`k3d-civitas-local-160` mit Ingress und `enable_gateway: false`. Die Abweichungen
vom unveränderten Core-Release, die lokalen Baikor-Artefakte und der bereits
geprüfte Wechsel vom Bootstrap-Admin zum Owner sind im
[Deployment-Review](core-1.6.0-deployment-review.md) dokumentiert.
Es handelt sich um einen Test auf der dort beschriebenen angepassten Core-1.6.0-
Umgebung, nicht um einen Nachweis für das produktive MDH-System.

## Einrichtung

1. **Publisher durch den lokalen Datenbankbetreiber bereitstellen.** Vorhandene
   Rolle und Secret wurden zuerst geprüft. Anschließend wurden ausschließlich
   `baikor_r_publisher` und `mdh-baikor-access/baikor-publisher` angelegt. Die Rolle
   hat `LOGIN`, aber kein `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION` oder
   `BYPASSRLS` und keine Rollenmitgliedschaften. Bestehende Zugangsdaten wurden
   nicht rotiert; es wurde kein Admin-Secret kopiert. Die Bereitstellung selbst
   vergibt keine Anwendungsrechte.
2. **Publikation im lokalen Owner-Inventar aktivieren.**
   `publication.enable: true` wird mit dem vorhandenen Workspace `ds_open_data`
   und Datastore `baikor-r` verwendet. Der Betriebsmodus bleibt
   `bootstrap.enable: true`, `admin_secret: baikor-owner`,
   `maintenance_database: baikor_r`, `generate_credentials: false`.
   `database.namespace: mdh-baikor-access` unterscheidet sich weiterhin vom
   Server-Namespace `tst-database-stack`. Die Owner-Jobs richten die fehlenden
   Publisher-Grants ein; der Owner erhält keine Rollenverwaltungsrechte.
3. **PostgreSQL-CA für GeoServer bereitstellen.** Der lokale Betreiber stellt
   die öffentliche Datenbank-CA als ConfigMap
   `tst-geodata-stack/local-geoserver-postgresql-ca`, Schlüssel `root.crt`, bereit.
   Das Deployment `geoserver-geoserver` bindet sie unter
   `/home/geoserveruser/.postgresql` schreibgeschützt ein.
   Die CA-Bereitstellung gehört zur Betreiberkonfiguration.
   Vor dem nächsten Add-on-Lauf muss der GeoServer-Rollout bereit sein.
4. **Optionale JNDI-Datenquelle einrichten.** Wegen des unten beschriebenen
   GeoTools-Fehlers wurde die vom Betreiber bereitgestellte Datenquelle
   `java:comp/env/jdbc/baikor` eingerichtet und über
   `publication.jndi_reference: java:comp/env/jdbc/baikor` aktiviert.
   Die lokale Tomcat-Konfiguration liegt im Secret
   `tst-geodata-stack/local-geoserver-baikor-context` und wird unter
   `/settings/context.xml` schreibgeschützt eingebunden. Ihre JDBC-URL verwendet
   `sslmode=verify-full`, den zertifikatskonformen Datenbank-Hostnamen und die
   bereitgestellte CA; der Login ist ausschließlich der Publisher.
   Core-Version und Container-Images bleiben dabei auf dem bisherigen Teststand.
   Der erfolgreiche Owner-Lauf hat beide Feature-Types publiziert. Die lesende
   REST-Prüfung bestätigt `PostGIS (JNDI)` und ausschließlich die Parameter
   `dbtype`, `jndiReferenceName`, `schema`; alte Inline-Zugangsdaten fehlen.
5. **Portal-Konfiguration zusammenführen und einbinden.** Für die
   Kartenintegration wird `publication.masterportal.enable: true` mit einem
   lokalen Exportverzeichnis gesetzt. Das Add-on exportiert
   `configure-masterportal.cjs`. Der Betreiber führt es mit `node` gegen die
   vorhandenen `config.json` und `services.json` aus und bindet die zusammengeführten
   Dateien über seine Portal-Konfiguration ein. Export allein aktiviert keine
   laufende Portal-Konfiguration. Im lokalen Test stellt die ConfigMap
   `tst-geodata-stack/local-geoportal-inputs` beide Dateien bereit. Das Deployment
   `portal-backend` bindet sie schreibgeschützt unter
   `/usr/src/app/input/default/config.json` und
   `/usr/src/app/input/default/services.json` ein.
   Der Betreiberlauf war erfolgreich (`ok=4 changed=2 failed=0`), die Wiederholung
   ohne Änderungen ebenfalls (`ok=4 changed=0 failed=0`). Die tatsächlichen
   HTTP-Konfigurationen des Backends enthalten den Baustellen-Layer und
   `specialWfs`; beide Abrufe lieferten HTTP 200.

## Testdaten und bereits bestätigte Ergebnisse

Die drei Datensätze wurden über die normale App-API mit Bearer-Authentifizierung
und CSRF-Token angelegt und wieder gelesen. Die 15 Prüfungen in
`checks-seed.json` sind erfolgreich. Sämtliche Namen, Kontakte und Freitexte sind
synthetisch; es wurden keine produktiven Baustellen oder personenbezogenen
Echtdaten verwendet.

| Testbaustelle | ID | Zustand | Öffentliche Flächen / Suchpunkte |
| --- | --- | --- | --- |
| TEST Core 1.6 Leitungsbau West | `2cd6ba85-346b-4857-ab00-fa6f71d32aad` | Approved | 2 / 1 |
| TEST Core 1.6 Strassensanierung Ost | `8afa8b93-d8db-45bc-b9e7-c7187cffe4e2` | Active | 1 / 1 |
| TEST Core 1.6 Entwurf Nord - nicht oeffentlich | `851edaad-670d-4989-b1cc-3087d4c9a147` | Draft | 0 / 0 |

Die lesenden Datenbankprüfungen verwenden den echten Publisher-Login und TLS
`verify-full`. Sie bestätigen die obigen Sichtbarkeiten, einen Suchpunkt in
EPSG:25832 je sichtbarer Baustelle, `security_barrier=true` für beide Views und
deren ausschließliche SELECT-Berechtigung. Der Publisher hat keine Rechte auf
Basistabellen; ein echter SELECT-Versuch auf `baikor.construction_sites` scheitert
mit SQLSTATE `42501`. Der Marker `PRIVATE_METADATA_NOT_FOR_PUBLICATION` erscheint
in keiner öffentlichen Projektion.

Die Flächenview veröffentlicht ausschließlich `id`, `construction_site_id`,
`area_name`, `title`, `status`, `status_label`, `planned_start`, `planned_end`,
`area_size_sqm`, `diversion`, `communications`, `updated_at` und `geometry`.
Die Suchview enthält nur `id`, `title` und `geometry`. Kontakte, Anhänge und
Metadaten sind keine View-Spalten. Die Migrationen gewähren SELECT auf die
öffentlichen Views auch `PUBLIC`; der Nachweis betrifft deshalb insbesondere die
Abschottung der privaten Basistabellen und keinen exklusiven View-Zugriff.

Die HTTP-Nachkontrolle nach dem Lebenszyklustest bestätigt **25 von 25 Prüfungen**:
genau die drei Beispiel-IDs sind weiterhin in der App vorhanden; anonymes WFS
liefert drei öffentliche Flächen und zwei Suchpunkte. Draft-Daten, private
Kontaktmarker und der Metadatenmarker fehlen. Die öffentlichen Eigenschaften
entsprechen der erlaubten Auswahl, und die geprüften Freitexte enthalten kein
HTML. WMS liefert ein gültiges PNG mit drei sichtbaren Polygonen;
GetFeatureInfo liefert die zugehörigen Baustellendetails.

Für den Lebenszyklus wurde eine zusätzliche synthetische Baustelle verwendet.
Alle **67 Prüfungen** bestanden für
`Draft → Approved → Active → Planned → Approved → Draft → Approved → DELETE`.
Flächen und Titelsuche reagierten jeweils unmittelbar auf die Änderungen,
einschließlich Rücknahme und Löschung; Titeländerungen und die auf 6.400 m²
veränderte Geometrie waren ebenfalls sichtbar. Die gemessenen Statuswechsel
benötigten im lokalen Lauf etwa 0,29 bis 0,95 Sekunden ohne Deployment; dies ist
keine zugesicherte Laufzeit. Die zusätzliche Testbaustelle wurde anschließend
gelöscht, die drei Beispiele bleiben erhalten.

Ein zusätzlicher lesender Abgleich von `pg_stat_activity` und `pg_stat_ssl`
weist die echte JDBC-Verbindung des GeoServer-Pods `10.42.1.33` zum Publisher
`baikor_r_publisher` in `baikor_r` nach: TLS 1.3,
`TLS_AES_256_GCM_SHA384`, 256 Bit. Dafür wurden keine Secrets gelesen und keine
Runtime-Ressourcen verändert. Die Serverstatistik belegt ausgehandeltes TLS;
die Zertifikats- und Hostname-Prüfung ergibt sich zusätzlich aus der
JNDI-Konfiguration und lässt sich nicht allein aus `pg_stat_ssl` ablesen.

Die anonyme Portal-Oberfläche zeigt die drei öffentlichen Polygone. Die Suchen
nach `Strassensanierung` und `Leitungsbau` liefern jeweils einen passenden
Baustellentreffer. Auswählen setzt einen Marker und zentriert die Karte. Ein Klick
auf die aktive Fläche zeigt den Titel, den Status „Laufend“, den Zeitraum
16.10. bis 15.11.2026, 4.225 m² sowie bereinigte Umleitungs- und Kommunikationstexte.
Die Suche nach `Entwurf Nord` liefert keinen Treffer. Der Screenshot
`geoportal-site-details.jpg` dokumentiert Trefferliste, Karte und Detailansicht.
Ein separater WFS-1.1-Aufruf per XML-POST lieferte ebenfalls HTTP 200, den korrekten
Leitungsbau-Titel und eine gemessene Antwortzeit von rund 0,34 Sekunden.

Die 29 gezielt ausgeführten Add-on-Tests einschließlich sechs JNDI-Prüfungen
und der separate Operator-Ownership-Test sind erfolgreich. Der abschließende
Clustercheck fand bei 38 Pods keine nicht bereiten laufenden Workloads;
abgeschlossene Jobs wurden dabei ausgenommen. Der letzte kombinierte lokale
Betreiber-Prüflauf blieb unverändert (`ok=14 changed=0 failed=0`).

## Prüfstand und beobachtete Fehler

| Prüfung | Aktueller Nachweis |
| --- | --- |
| Erster Publikationslauf | DB-Owner-Jobs erfolgreich; GeoServer-REST-Aufruf scheiterte während des CA-Rollouts vor Betriebsbereitschaft. Recap: `ok=94 changed=5 failed=1`. |
| Wiederholung nach Readiness | Beim Anlegen beider Feature-Types fehlgeschlagen. GeoTools übergibt den Enum-Namen `VERIFY_FULL` an PgJDBC, das diesen JDBC-Parameter ablehnt. Recap: `ok=100 changed=5 failed=1`. |
| Versuch mit kleingeschriebenem SSL-Modus | Ebenfalls beim Anlegen beider Feature-Types fehlgeschlagen; `verify-full` scheitert bereits an der Enum-Konvertierung in GeoTools. `publication-deploy-fixed.log`: `ok=100 changed=5 failed=1`. Diese Änderung wurde zurückgenommen. |
| Optionale JNDI-Datenquelle | Owner-Deployment erfolgreich: `publication-deploy-jndi.log`, `ok=107 changed=7 failed=0 skipped=22`. Tatsächlicher Datastore, beide Feature-Types und TLS-Verbindung geprüft. |
| Anonymes WFS und WMS/GetFeatureInfo | Bestanden; 25 Prüfungen einschließlich Nachkontrolle der drei verbleibenden App-Datensätze. |
| Portal-Konfiguration | Tatsächlich im Backend eingebunden und über HTTP geprüft; Betreiberlauf erfolgreich und bei Wiederholung ohne Änderungen. |
| Portal-Karte, Flächenauswahl und Titelsuche | Bestanden; drei Polygone, passende Treffer, Marker und Details, kein Treffer für den Entwurf. Separater WFS-XML-POST ebenfalls erfolgreich. |
| Statuswechsel, Titel, Geometrie und Löschung | Bestanden; 67 Prüfungen mit separater, anschließend gelöschter Testbaustelle. |

**Beobachtung beim Kaltstart:** Zwei erste Suchaufrufe in der Oberfläche nach
einem GeoServer-Neustart liefen in einen Timeout. Parallel initialisierte
GeoServer die XML-WFS-Verarbeitung und verarbeitete den Request verzögert.
Nach der Initialisierung waren die Wiederholungen und der separate XML-POST
erfolgreich. Im Test blieb damit kein dauerhafter Suchfehler bestehen; die
anfängliche Verzögerung ist eine Betriebsgrenze dieses lokalen Kaltstarts.
Es wurde keine Erhöhung der Timeouts implementiert.

Die Views filtern nach Status, nicht nach Planungsdatum. Freitextbereinigung
entfernt teilweise HTML und vereinheitlicht Leerzeichen; sie anonymisiert keine
Inhalte. Der lokale Test mit erfundenen Daten ersetzt keine fachliche Freigabe
oder Datenschutzprüfung vor einer produktiven Veröffentlichung.

Die bestätigte Ursache liegt in `getJDBCUrl` von GeoTools 34.0: Die Methode hängt
das Enum-Objekt `mode` an die JDBC-URL an und übergibt dadurch `VERIFY_FULL`
statt des JDBC-Werts `verify-full`. Im Quellcode von GeoTools 34.5 wird dafür
`mode.value` verwendet. Siehe die Quellen von
[GeoTools 34.0](https://github.com/geotools/geotools/blob/34.0/modules/plugin/jdbc/jdbc-postgis/src/main/java/org/geotools/data/postgis/PostgisNGDataStoreFactory.java)
und
[GeoTools 34.5](https://github.com/geotools/geotools/blob/34.5/modules/plugin/jdbc/jdbc-postgis/src/main/java/org/geotools/data/postgis/PostgisNGDataStoreFactory.java).

Die zuvor geprüfte Kleinschreibung im Add-on behebt diesen Fehler nicht.
Das unabhängige Review, sechs erfolgreich gerenderte Parameterkombinationen,
23 bestandene Unit-Tests und der bestandene Operator-Ownership-Test unter
Windows belegten keine funktionierende GeoTools-/PgJDBC-Verbindung.
Der geprüfte JNDI-Weg stellt die JDBC-Verbindung mit Zertifikats- und
Hostname-Prüfung direkt bereit. Dafür wurden weder TLS abgeschwächt noch
das GeoServer-Image ausgetauscht. Dieser Weg ist eine optionale, vom Betreiber
einzurichtende Integration; der direkte Datastore mit GeoTools 34.0 bleibt von
dem Upstream-Fehler betroffen.

## Nachweise

Lokales Nachweisverzeichnis:
`%TEMP%\baikor-geoportal-20261016-104044`.

- Einrichtung: `publisher-provisioning-proof.json`, `provision_publisher.py`.
- App-Datensätze: `test-sites.json`, `checks-seed.json`, `test_geoportal.py`.
- Datenbank: `publisher-verification.json`, `publisher-site-approved.json`,
  `publisher-site-active.json`, `publisher-site-draft.json`, `verify_publisher.py`.
- GeoServer und TLS: `geoserver-verification.json`, `verify_geoserver.py`,
  `geoserver-database-tls-proof.json`, `verify_geoserver_database_tls.py`.
- WFS/WMS: `checks-verify.json`, `published-areas.json`, `published-search.json`,
  `map-feature-info.json`, `construction-sites-wms.png`.
- Portal-Oberfläche und Suche: `geoportal-site-details.jpg`,
  `browser-verification.json`, `wfs-search-post.json`, `verify_wfs_search.py`.
- Portal-Konfiguration: `portal-http-config-proof.json`, `verify-portal-http.py`,
  `portal-operator-repeat-check.log`; Cluster: `final-cluster-health.json`.
- Lebenszyklus: `checks-transitions.json`; die Löschung der zusätzlichen
  Testbaustelle ist außerdem in `test-sites.json` festgehalten.
- Deployment: `publication-deploy.log`, `publication-deploy-ready.log`,
  `publication-deploy-fixed.log`, `publication-deploy-jndi.log`.

Die Nachweise enthalten keine Passwörter oder Token und werden nicht als
Deployment-Konfiguration eingecheckt. GitNexus-Impact für dieses neue Dokument
lieferte `UNKNOWN`/nicht indexiert; die ergänzende Referenzsuche wurde deshalb
zusätzlich durchgeführt. Das vorherige Deployment-Review verweist inzwischen
auf diesen Folgetest. Die bestehenden Quellen und die Nachweise wurden direkt
geprüft.
