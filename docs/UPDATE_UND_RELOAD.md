# Update- und Reload-Verhalten – VerbrauchsMonitor

Home Assistant importiert Python-Module beim Start. Ein Config-Entry-Reload entlädt und lädt die Integrationseinträge und ihre Plattformen neu, importiert bereits geladene Python-Dateien aber nicht erneut. Deshalb gelten folgende Regeln:

| Änderung | Erforderliche Aktion |
|---|---|
| Nur Lovelace-JavaScript/CSS geändert | Dashboard bzw. Browser neu laden; ggf. Cache aktualisieren. |
| Vertrags-, Zähler- oder Optionsdaten über die Integrationsoberfläche geändert | Speichern verwendet den Config-Entry-Reload. |
| Quell-Sensorzustand ändert sich | Die Integration aktualisiert abhängige Sensoren ereignisgesteuert bzw. über den jeweiligen Aktualisierungszyklus. |
| Python-Dateien geändert | Vollständiger Home-Assistant-Neustart erforderlich. Ein Integrations-Reload reicht nicht zum erneuten Import des Codes. |
| `manifest.json`, Plattformregistrierung oder Abhängigkeiten geändert | Home Assistant vollständig neu starten. |
| YAML-Ressourcenmodus verwendet | Sicherstellen, dass `/verbrauchsmonitor/verbrauchsmonitor-card.js` als Ressource vom Typ `module` eingetragen ist; danach Dashboard neu laden. |

## Updateablauf

1. Vor dem Update ein Home-Assistant-Backup erstellen.
2. Den vollständigen Ordner `custom_components/verbrauchsmonitor/` austauschen; keine alten Dateien im Integrationsordner zurücklassen.
3. Bei Änderungen an Python, Manifest oder Plattformregistrierung Home Assistant vollständig neu starten.
4. Nach reinen Frontend-Änderungen Dashboard/Browser neu laden.
5. Nach dem Start die Integrationsdiagnose, vorhandene Zähler, Sensoren, Karten und Buchungen kontrollieren.
6. Bei Datenbank- oder Schemaänderungen die im Releasebericht beschriebenen Migrationen und Hinweise beachten.

## Daten und Rückfall

Die Integrationskonfiguration wird über den Config Entry verwaltet. Fachliche Buchungsdaten liegen im lokalen Integrationsdatenspeicher. Vor Updates mit Datenmodell- oder Migrationsänderungen ist eine Home-Assistant-Sicherung erforderlich. Ein Downgrade darf nicht als sicher gelten, wenn ein neuerer Datenbankschemastand geschrieben wurde; vor einem Rückfall ist die Sicherung des vorherigen Stands wiederherzustellen.
