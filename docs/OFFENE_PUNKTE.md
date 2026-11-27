## R161 – Anzeigenamen Tageswertsensoren
- [x] Anzeigenamen auf `TagesVerbrauch` und `TagesEinspeisung` geändert.
- [x] Bekannte automatisch erzeugte R160-Namen werden gezielt migriert.
- [x] Individuelle Registry-Namen bleiben erhalten.
- [x] Entity-IDs und Tageswertdaten bleiben unverändert.
- [ ] Sichtprüfung der aktualisierten Entity-Registry im laufenden Home Assistant.

## R155 – Tageswerte je Zähler
- [x] Zusätzliche Entität „Verbrauch (heute)“ für jeden konfigurierten Verbrauchszähler.
- [x] Zusätzliche Entität „Einspeisung (heute)“ nur bei konfigurierter Einspeisung.
- [x] Tagesbasis lokal und dauerhaft je Zähler/Richtung speichern und nach Neustarts wiederherstellen.
- [x] Bei fehlender Tagesbasis den Tagesbeginn soweit möglich aus der Recorder-Historie rekonstruieren; andernfalls keinen erfundenen Wert anzeigen.
- [ ] Laufzeittest in Home Assistant mit echtem Recorder und einem Zählerwechsel durchführen.

# Open Points and Runtime Verification

This file deliberately distinguishes implemented/tested behavior from work that cannot be verified without a running Home Assistant installation.

## Runtime checks required before production use

1. Install Beta R152 over R151 and verify that the primary and backup learning stores are both loaded, that a missing/empty primary is restored from the backup, and that consumption/feed-in histories remain isolated. Confirm that neither store is removed by the integration update.

2. Install Beta R124 over a backup copy of the current installation.
3. Confirm the integration starts and unloads without errors.
4. Confirm the entity registry renames only this integration's legacy balance IDs to the canonical `sensor.verbrauchsmonitor_<meter>_verbrauch_kontostand` and `sensor.verbrauchsmonitor_<meter>_einspeisung_kontostand` IDs.
5. Confirm history retention behavior for renamed entities in the actual Recorder database.
6. Confirm the database status reports contract and logical meter counts from config-entry options, and ledger counts from SQLite.
7. Confirm a monthly advance edit recalculates the balance entities immediately after the options-flow save/reload.
8. Confirm negative monthly advance values are rejected and `0` is accepted.
9. Confirm the initial reliability value is marked as an initialization; a provisional recommendation is shown only when at least two future payment dates remain and a positive payment gap remains after booked and scheduled payments. Measured reliability appears only after 24 completed hourly comparisons.
10. Confirm the current-month average changes with the current local time and uses the exact elapsed time since billing-period start.
11. Confirm hourly forecast records are persisted across restart and compared with the correct completed Recorder hour.
12. Confirm consumption and feed-in learning remain isolated per meter and direction.
13. Confirm solar position, calculated local sunrise/sunset, daylight duration, DST transitions, and selected compass directions in the target location for both consumption and feed-in forecasts.
14. Confirm the card layout, localized currency/number formatting, and translations in both German and English.
15. Implement the requested two-column compass-direction checkbox layout using a custom config-flow frontend; the native Home Assistant selector has no supported column-layout parameter. R128 already supports per-meter optional multi-selection and south as the default for new feed-in meters.

## Known functional limitations

- The first-install solar and direction profiles are generic priors, not a physical PV simulation. Exported feed-in does not represent total PV generation when self-consumption or storage is present.
- Candidate learning uses a bounded global scale correction with a chronological holdout comparison; it is not a high-dimensional or machine-learning optimization model.
- If Recorder cannot provide consecutive hourly cumulative statistics, the affected hours are skipped rather than inferred. The learner therefore requires a running Recorder and sufficiently regular statistics.
- A real Home Assistant runtime test is required for selectors, config-entry reload behavior, Recorder integration, entity-registry migration, and frontend rendering.
- The requested two-column compass-direction checkbox layout remains unimplemented. R128 provides German/English labels and per-meter multiple selection; Home Assistant native list selectors render vertically.
- The solar-aware profiles are deterministic priors/refinements, not weather forecasts or a physical PV simulation. The target installation must verify that the local timezone and configured Home Assistant coordinates are correct.
- Historical tariff snapshots and immutable billing-period closing snapshots remain outstanding project-level requirements.

## Release gate

Do not promote this package to production until the runtime checks above are completed and their results are documented. Automated test success alone is not a production certification.


## R128 – weiterhin offen
- Die Mehrfachauswahl der Himmelsrichtungen ist je Einspeisungszähler umgesetzt. Die native Home-Assistant-Formularauswahl kann jedoch nicht zuverlässig zweispaltig dargestellt werden; hierfür ist eine eigene Frontend-Konfiguration erforderlich.
- Home-Assistant-Laufzeittest und visuelle Prüfung im Zielsystem stehen aus.

## R152 – weiterhin offene Lern-/Kalibrierungspunkte
- Die Primär- und Sicherungsdatei des Lernverlaufs müssen nach Installation über R151 in einem echten Home-Assistant-System praktisch auf Wiederherstellung geprüft werden.
- Ein Neustart- und Update-Test mit bereits gefülltem Lernverlauf steht aus; automatisierte Tests prüfen Speicherkennung, Sicherungspfad und Restore-Logik, ersetzen aber keinen echten HA-Laufzeittest.
- Die rückwirkende Bewertung vorhandener Recorder-Messwerte ohne gespeicherte historische Prognosen ist fachlich noch nicht gleichbedeutend mit einem Prognose-/Ist-Vergleich. Es dürfen dafür keine historischen Prognosen erfunden werden.
- Die Kalibrierung, ob ein früher angezeigter Zuverlässigkeits-Prozentwert später tatsächlich der erreichten Prognosequalität entspricht, bleibt offen.
- Der finanzielle Prognosevergleich mit tatsächlich abgeschlossenen Abrechnungen bleibt offen; das Finanzmodul wird bis zu einer belastbaren Vergleichshistorie nicht als gemessene Prognosegenauigkeit ausgegeben.
- Der langfristige Nachweis einer Verbesserung über mehrere Abrechnungszeiträume/Jahre ist erst nach entsprechendem Echtbetrieb möglich.


## R154 – Fortschrittsanzeige
- Fortschritt der initialen Berechnungsphasen wird in der bestehenden Kartenanzeige ausgegeben. Der Wert ist von der fachlichen Zuverlässigkeit getrennt.
- Der Fortschritt wird je Sensorlaufzeit monoton gespeichert. Bei späteren Neuberechnungen bleibt der erreichte Fortschrittsstand erhalten; der Spinner signalisiert die laufende Aktualisierung. Eine feinere Fortschrittsanzeige pro Neuberechnung ist erst sinnvoll, wenn die Berechnung in explizit messbare Teilaufgaben mit einer stabilen, dynamischen Arbeitswarteschlange zerlegt wird.
- Visuelle Prüfung im echten Home-Assistant-Frontend steht aus.


## R156 – Zuverlässigkeitsgrundlage aus vorhandener Recorder-Historie
- [x] Ursache behoben: Die Zuverlässigkeitsauflösung hat ausschließlich neue Forecast-Ist-Paare berücksichtigt und vorhandene Recorder-Historie trotz ausreichender Datenbasis ignoriert.
- [x] Vorhandene, nutzbare Recorder-Historie liefert jetzt eine initiale Bewertung aus Dauer, Abdeckung, Kontinuität, Plausibilität und verwendeter Prognosemethode.
- [x] Initiale Historienqualität wird ausdrücklich von gemessener Prognosegenauigkeit unterschieden. Ab 24 gültigen stündlichen Prognose-Ist-Vergleichen haben die echten Vergleiche Vorrang.
- [ ] Laufzeittest mit der tatsächlichen Recorder-Historie für Verbrauch und Einspeisung durchführen.


## R157 – Tageswertsensoren und Recorder-Kompatibilität
- [x] Recorder-Historie für die Tagesbasis wird über den Recorder-eigenen Executor abgefragt.
- [x] Energie-Tageswertsensoren verwenden die zulässige Zustandsklasse `total_increasing`.
- [x] Bekannte fehlerhafte Registry-Bezeichnung `(heute)` wird auf den vollständigen Namen korrigiert; andere benutzerdefinierte Namen werden nicht überschrieben.
- [ ] Laufzeittest im Zielsystem: Recorder-Abfrage ohne Executor-Warnung.
- [ ] Prüfen, dass Verbrauch (heute) und Einspeisung (heute) im Gerätebereich vollständig benannt und mit gültigem Zustand erscheinen.
- [ ] Mitternachtswechsel, Neustart am selben Tag und Zählerwechsel mit echten Quellzählern prüfen.
- [ ] Langzeitstatistiken im Home-Assistant-Recorder nach einem Tagesreset kontrollieren.


## R158 – Zuverlässigkeitsinitialisierung und Tageswertsensoren
- [x] Initiale Zuverlässigkeitsbewertung kann bei fehlender langer Recorder-Historie auf tatsächlich vorhandene Live-Messwert- und Konfigurationsqualität zurückgreifen; die Basis wird ausdrücklich nicht als gemessene Prognosegenauigkeit bezeichnet.
- [x] Optionale, nicht konfigurierte Wetterentitäten werden nicht als fehlende Daten gewertet.
- [x] Tagesbasis kann zusätzlich aus Recorder-Langzeitstatistiken rekonstruiert werden, wenn signifikante Zustände nicht verfügbar sind.
- [x] Bekannte automatisch erzeugte Kurzbezeichnungen werden korrigiert; manuelle Umbenennungen bleiben erhalten.
- [ ] Praktischer Test mit der tatsächlichen Recorder-Historie und Entity-Registry des Nutzers bleibt erforderlich.
- [ ] Mitternachtswechsel, HA-Neustart, Zählerwechsel und Langzeitstatistiken müssen im Zielsystem praktisch bestätigt werden.


## R159 – Zuverlässigkeitsqualität und Tageswertnamen
- [x] Initiale Zuverlässigkeit wird nicht mehr allein durch Historien-Datenqualität und eine aggressive vierte Wurzel des Zeitfortschritts hochgezogen; Evidenz-Konfidenz und konservativere Zeitgewichtung sind implementiert.
- [x] Verbrauch und Einspeisung werden in separaten Bewertungs-/Lernpfaden gehalten; die Bewertung berücksichtigt die jeweilige Historienqualität.
- [x] Energiegewichtete Fehlerbewertung schützt Einspeisungsprognosen vor einer Dominanz sehr kleiner oder nächtlicher Nullwerte.
- [x] Legacy-Registry-Namen „(heute)“ werden anhand von `name` oder `original_name` korrigiert, explizite benutzerdefinierte Namen bleiben unangetastet.
- [x] Tageswerte werden weiterhin als steigende Differenz zum gespeicherten Tagesbeginn berechnet und verwenden `total_increasing`.
- [ ] Im Zielsystem prüfen, dass der Entity-Registry-Name nach Reload tatsächlich „Verbrauch (heute)“ bzw. „Einspeisung (heute)“ lautet.
- [ ] Im Zielsystem steigende Tageswerte, Mitternachtsreset, Neustart und Recorder-Statistiken mit echten Quellzählern bestätigen.
- [ ] Für den Einspeisungs-Lernpfad saisonale Prognosequalität über einen vollständigen Sommer-/Winterzyklus mit echten PV-Daten prüfen.
- [ ] Wetterentitäten als echte Prognosemerkmale erst dann stärker gewichten, wenn ihre Vorhersagewirkung anhand unabhängiger Vergleichsdaten nachgewiesen wurde; bloße Konfiguration darf keinen Bonus erzeugen.


## R160 – Tageswertsensoren: Name und steigender Wert
- [x] Entity-Anzeigenamen so geändert, dass Home Assistant sie in der Geräteansicht nicht mehr auf den Präfixrest `(heute)` verkürzt: `Tagesverbrauch (heute)` und `Tages-Einspeisung (heute)`.
- [x] Bekannte automatisch erzeugte Altbezeichnungen werden migriert; ausdrücklich abweichende benutzerdefinierte Namen bleiben erhalten.
- [x] Wenn Recorder und Langzeitstatistiken keine Mitternachtsbasis liefern, wird der reale aktuelle kumulierte Zählerstand als persistente Teil-Tagesbasis verwendet. Der Tageswert steigt ab diesem Zeitpunkt; `partial_day: true` weist transparent darauf hin, dass der frühere Tagesanteil nicht rekonstruierbar war.
- [x] Teil-Tageskennzeichnung und Basis werden über Home-Assistant-Neustarts wiederhergestellt.
- [x] Automatisierte Verhaltenstests für Namen, Registry-Migrationsentscheidung, Tagesbasis, steigende Differenzwerte und Neustart-Wiederherstellung ergänzt.
- [ ] Im Zielsystem nach Reload kontrollieren, dass die Registry die Namen `Tagesverbrauch (heute)` und `Tages-Einspeisung (heute)` zeigt.
- [ ] Mit realen Zähleränderungen bestätigen, dass die Werte im Tagesverlauf steigen und `partial_day` bei fehlender Mitternachtshistorie korrekt gesetzt ist.
- [ ] Nach Neustart am selben Tag prüfen, dass die Tagesbasis unverändert bleibt.
- [ ] Mitternachtswechsel und Recorder-Langzeitstatistiken im echten Home Assistant prüfen.
- [ ] Bei manuell umbenannten Entitäten bestätigen, dass die Namen nicht überschrieben werden.
