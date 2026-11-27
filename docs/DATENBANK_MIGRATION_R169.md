# Datenbankmigration R169 – gestufte SQLite-Trennung

## Ziel

Die bisherige SQLite-Snapshot-Struktur wird um fachlich getrennte Tabellen erweitert. Die Migration ist bewusst gestuft: Die vorhandene `vm_state`-Snapshot-Tabelle bleibt als Kompatibilitäts-, Export- und Wiederherstellungsbasis bestehen. Die getrennten Tabellen sind für die unten aufgeführten Datensatzbereiche bereits die maßgebliche Lesequelle.

## Tabellen

| Tabelle | Inhalt | Wichtige Zuordnungsfelder |
|---|---|---|
| `vm_contracts` | Vertrags-Stammdaten | `record_id`, `entry_id` |
| `vm_meters` | logische Zähler | `record_id`, `entry_id`, `contract_id` |
| `vm_bookings` | Buchungen und Korrekturen | `record_id`, `meter_id`, `contract_id`, `direction` |
| `vm_physical_meter_periods` | physische Zählerabschnitte | `record_id`, `meter_id`, `direction`, `installed_at` |
| `vm_advance_rates` | zeitlich gültige Abschlagsraten | `record_id`, `meter_id`, `contract_id`, `direction`, `effective_from` |
| `vm_monthly_advances` | monatliche Abschlagswerte und Historie | `record_id`, `meter_id`, `direction`, `month` |
| `vm_migration_state` | Migrationsstatus | `state_key` |

Jede Tabelle bewahrt den vollständigen ursprünglichen Datensatz als JSON-Payload. Die Zuordnungsfelder erlauben gezielte Indizes und spätere relationale Abfragen, ohne beim ersten Migrationsschritt unbekannte Alt-Felder zu verlieren.

## Migrationsablauf

1. Die bisherige Datenbank wird erkannt und ihre `user_version` geprüft.
2. Vor der Schema-1-Umstellung wird – sofern noch nicht vorhanden – `verbrauchsmonitor-pre-r169-backup.db` als separate, nicht automatisch überschriebene Sicherung angelegt.
3. Die Tabellen und Indizes werden idempotent angelegt.
4. Vorhandene Snapshot-Datensätze werden in die getrennten Tabellen übertragen. Datensätze ohne ID oder mit mehrfach verwendeter ID erhalten nur einen deterministischen technischen Primärschlüssel; ihr ursprünglicher Payload bleibt unverändert.
5. Erst nach erfolgreichem Backfill wird `PRAGMA user_version` auf 2 gesetzt.
6. Bei jedem anschließenden Schreibvorgang werden Snapshot und getrennte Datensatzbereiche innerhalb derselben SQLite-Transaktion synchronisiert.
7. Beim Setup werden Verträge und logische Zähler aus allen aktiven Config-Entries erneut in ihre Tabellen synchronisiert. Die Home-Assistant-Config-Entry-Optionen bleiben in diesem Entwicklungsstand deren Konfigurationsquelle.

## Rückwärtskompatibilität und Grenzen

- `vm_state` bleibt vorerst für vorhandene Import-/Export- und Wiederherstellungswege erhalten.
- `_read()` bezieht die Datensatzbereiche aus den getrennten Tabellen; der Snapshot allein kann diese Datensätze nicht mehr überschreiben.
- Verträge und logische Zähler bleiben bis zu einer gesonderten Config-Flow-Umstellung in den Config-Entry-Optionen führend und werden beim Setup in SQLite projiziert.
- Die relationalen Tabellen verwenden Fremdschlüssel mit `ON DELETE SET NULL`. Ungeklärte Altzuordnungen werden nicht geraten: Die relationale Referenz bleibt NULL, der vollständige Originalverweis bleibt im Payload erhalten.
- Es werden keine Periodenwerte, Tages-/Wochen-/Monats-/Jahresdaten oder Referenzstände gelöscht oder neu berechnet.

## Verifikation

Die Tests prüfen Schema-1-Backfill, Schema-Version, SQLite-Integrität, Vor-Migrationsbackup, Lesepriorität der getrennten Tabellen, Erhalt von Datensätzen ohne ID bzw. mit doppelten IDs und Synchronisierung von Config-Entry-Projektionen.

## Relationale Integrität

Die Tabellen `vm_meters`, `vm_bookings`, `vm_physical_meter_periods`, `vm_advance_rates` und `vm_monthly_advances` verwenden Fremdschlüssel auf die jeweils vorhandenen Vertrags- und Zählerdatensätze. Beim Backfill werden nur tatsächlich auflösbare Beziehungen in den relationalen Spalten gesetzt. Unaufgelöste historische Verweise bleiben vollständig im JSON-Payload erhalten und werden nicht durch erfundene Zuordnungen ersetzt. `ON DELETE SET NULL` verhindert, dass eine entfernte Konfiguration historische Buchungs-Payloads kaskadierend löscht.

Die Home-Assistant-Config-Entry-Optionen bleiben in R169 die führende Quelle für Vertrags- und Zählerkonfiguration. Die SQLite-Tabellen sind hierfür eine zusätzliche relationale Projektion. Eine spätere vollständige Verlagerung der Konfigurationshoheit in SQLite ist ausdrücklich nicht Teil von R169.
