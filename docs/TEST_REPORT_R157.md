# Testbericht Beta R157

## Umgesetzte Korrekturen
- Recorder-Abfrage für die Wiederherstellung der Tagesbasis nutzt `recorder.get_instance(hass).async_add_executor_job(...)`.
- Tageswertsensoren verwenden `device_class: energy` mit `state_class: total_increasing`.
- Ausschließlich die bekannte fehlerhafte Entity-Registry-Bezeichnung `(heute)` wird auf den vollständigen Richtungsnamen korrigiert. Individuelle andere Namen bleiben unangetastet.

## Automatisierte Prüfungen
- `python -m compileall -q custom_components/verbrauchsmonitor`: erfolgreich.
- `pytest -q`: 524 Tests bestanden.
- JSON-Syntax: 4 JSON-Dateien erfolgreich geparst.
- JavaScript-Syntax (`node --check`): erfolgreich.
- Deutsche und englische Übersetzungsdateien: vorhanden; vollständiger Strukturvergleich ist Teil der zusätzlichen Releaseprüfung.

## Nicht durchführbar in dieser Umgebung
- Kein vollständiger Home-Assistant-Laufzeittest mit Recorder-Datenbank und Entity Registry.
- Kein praktischer Test des Mitternachtswechsels, eines Neustarts am selben Tag oder eines physischen Zählerwechsels.
- Langzeitstatistiken nach täglichem Reset müssen im Zielsystem kontrolliert werden.

Automatisierte Tests ersetzen diese Laufzeitprüfungen nicht.
