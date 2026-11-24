# Technische Architektur – VerbrauchsMonitor

## Architekturziele

- Home-Assistant-Anbindung, Fachlogik, Persistenz und Frontend sind getrennt.
- Ein Config Entry verwaltet den Integrations-Hub; darin können mehrere Verträge und logische Zähler konfiguriert werden.
- Verbrauch und Einspeisung werden fachlich getrennt geführt.
- Persistente Kennungen sind sprachunabhängig und unabhängig von Anzeigenamen.
- Datenverarbeitung und Speicherung erfolgen lokal. Es gibt keine ungefragte Telemetrie.

## Modulverantwortung

| Datei/Verzeichnis | Verantwortung |
|---|---|
| `__init__.py` | Setup/Unload des Config Entries, Kartenregistrierung, Registry-Bereinigung, Migration und wiederkehrende Baseline-Prüfung |
| `config_flow.py` | Ersteinrichtung, Options Flow, Vertrags-/Zählerverwaltung, Buchungen, Abschläge, Prognoseoptionen und Datenverwaltungsdialoge |
| `const.py` | Domain, Konfigurationsschlüssel, Plattform- und Frontend-Konstanten sowie Integrationsversionskennung |
| `sensor.py` | Native Sensorentitäten, Zustands-/Attributbereitstellung und Anbindung der Backend-Berechnungen |
| `database.py` | Lokale persistente Daten, Buchungsverwaltung, Import/Export, Integritätsprüfung und Reset-Funktionen |
| `ledger.py` | Buchungs- und Kontostandslogik einschließlich automatischer Monatsabschläge |
| `pricing.py` | Preis- und Steuerberechnungen mit Dezimalarithmetik und zentralen Rundungsregeln |
| `forecast.py` | Verbrauchs-/Einspeiseprognose, Recorder-Datenbasis, saisonale Gewichtung und Zuverlässigkeitsbewertung |
| `seasons.py` | Lokale astronomische Jahreszeitenberechnung anhand der Home-Assistant-Koordinaten |
| `naming.py` | Kanonische Entity-IDs und Unique-ID-bezogene Namensbildung |
| `registry_cleanup.py` | Ermittlung erwarteter Entitäten und gezielte Bereinigung veralteter Registry-Einträge |
| `frontend/` | Registrierung und Implementierung der Lovelace-Abrechnungskarte |
| `translations/` und `strings.json` | Deutsche und englische UI-Texte für Home Assistant |

## Datenmodell und Zuständigkeiten

- **Verträge** enthalten Vertragsdaten, Abrechnungszeitraum, Preis-/Steuerparameter und vereinbarte Abschläge.
- **Logische Zähler** referenzieren einen Vertrag und optional die Quellentitäten für Bezug, Einspeisung und ergänzende Messwerte.
- **Messrichtungen** `consumption` und `feed_in` werden unabhängig berechnet und dargestellt.
- **Buchungen** werden einem logischen Zähler und einer Messrichtung zugeordnet. Nicht eindeutig zuordenbare Legacy-Daten bleiben ungeklärt, statt automatisch einem Zähler zugeordnet zu werden.
- **Baselines** für Abrechnungsperioden speichern Wert, Herkunft und Datum. Routineübernahmen und manuelle Korrekturen werden historisiert.
- **Prognosen** sind Anzeige-/Planungswerte. Sie erzeugen keine Buchungen und verändern den aktuellen Kontostand nicht.

## Abschlags- und Kontostandsberechnung

Ein vertraglicher Monatsabschlag gilt an jedem Monatsersten innerhalb des Abrechnungszeitraums automatisch als geleistet. Eine explizite Abschlagsbuchung für denselben Monat ersetzt den automatischen Monatsbetrag, damit keine Doppelzählung entsteht. Verbrauchs- und Einspeisungsabschläge bleiben getrennt. Zukünftige Zahlungstermine werden nur als erwartete Zahlungen in Prognosen berücksichtigt.

Buchungsarten wie Sonderzahlung, Gutschrift und Korrektur werden separat gespeichert. Der Saldo wird aus Kosten/Erlösen und den fachlich zugeordneten Buchungen berechnet. Negative Salden bedeuten aus Kundensicht eine Verbindlichkeit, positive Salden ein Guthaben.

## Preise und Rundung

Preiswerte werden intern mit Dezimalarithmetik verarbeitet. Netto-/Brutto-Eingaben werden anhand der Steuerkennzeichnung interpretiert; die Tarifpräzision bleibt für Berechnungen erhalten. Geldbeträge werden nach der zentralen kaufmännischen Regel (`ROUND_HALF_UP`) je Abrechnungsposition auf Cent gerundet; Gesamtsummen werden aus den gerundeten Positionen gebildet. Die Lovelace-Karte zeigt die Backend-Ergebnisse und enthält keine eigenständige zweite Fachberechnung.

## Prognose

Die Prognose liest die verfügbaren Home-Assistant-Recorder-Daten je Quellentität und Messrichtung. Langzeitstatistiken werden bevorzugt; Detailhistorie ist ein Fallback. Saisonale Gewichtung wird nur bei ausreichender Historienlänge und Datenqualität eingesetzt. Bei fehlender oder unplausibler Datenbasis wird auf eine lineare Methode zurückgefallen. Die astronomische Jahreszeit wird lokal anhand des Home-Assistant-Standorts ermittelt.

Der Zuverlässigkeitswert bewertet unter anderem Historienlänge, Datenabdeckung, Messlücken, Plausibilität und verwendete Prognosemethode. Der persistente Zustand beschränkt sich auf den aktuellen Wert und den Aktualisierungszeitpunkt, nicht auf stündliche Verlaufsdatensätze.

## Persistenz und Migration

Die Konfiguration wird über den Home-Assistant-Config-Entry verwaltet. Fachliche Buchungsdaten liegen in `/config/verbrauchsmonitor.db` in einer lokalen SQLite-Datenbank. Die Daten werden als validierter Snapshot innerhalb einer SQLite-Transaktion gespeichert; SQLite verwendet WAL-Modus, aktivierte Foreign-Key-Prüfung und `synchronous=FULL`. Die einzelne rollierende Sicherung liegt unter `/config/verbrauchsmonitor-backup.db` und wird über die SQLite-Backup-API konsistent aktualisiert. Die fachliche Payload-Schemaversion bleibt getrennt von der SQLite-Dateischemaversion. Der frühere JSON-Bestand unter `.storage/verbrauchsmonitor_data.json` wird beim ersten Zugriff einmalig migriert und nicht gelöscht. JSON bleibt das validierte Austauschformat für Import und Export. Reset-Funktionen sichern den vorherigen SQLite-Stand zunächst in der Backup-Datei und müssen über den vorgesehenen Bestätigungsablauf ausgelöst werden.

Die Migration älterer Config Entries überführt das frühere Einzelzähler-Modell in das zentrale Hub-Modell. Legacy-Buchungen ohne eindeutige Zuordnung werden nicht stillschweigend verrechnet.

## Home-Assistant-Lifecycle

Beim Setup wird die Kartenressource idempotent registriert, die Entity Registry gegen die erwarteten Unique IDs abgeglichen, persistente Daten geladen und die Sensorplattform eingerichtet. Listener und Zeit-Callbacks werden über den Config-Entry-Lifecycle registriert und beim Unload entfernt. Optionsänderungen verwenden den Config-Entry-Reload.

Geänderte Python-Dateien werden durch einen vollständigen Home-Assistant-Neustart geladen. Ein Integrations-Reload importiert Python-Module nicht erneut.

## Bekannte Grenzen

Die noch offenen fachlichen und Zielsystempunkte sind in `OFFENE_PUNKTE.md` aufgeführt. Dazu gehören insbesondere vollständige physische Zählerwechsel-/Segmenthistorie, zeitliche Preisgültigkeit und Abrechnungssnapshots sowie Tests unter einer laufenden Home-Assistant-Instanz mit realen Recorder-Daten.
