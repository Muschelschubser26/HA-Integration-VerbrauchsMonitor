# Testbericht VerbrauchsMonitor Beta R161

## Änderungsumfang

- Anzeigename Verbrauch: `TagesVerbrauch`.
- Anzeigename Einspeisung: `TagesEinspeisung`.
- Der redundante Zusatz `(heute)` wurde entfernt.
- Bekannte automatisch erzeugte R160-Registry-Namen `Tagesverbrauch (heute)` und `Tages-Einspeisung (heute)` werden beim Laden der Entität auf die neuen Namen aktualisiert.
- Individuelle Namen, Entity-IDs, Unique-IDs, Tagesbasis und Messwertberechnung bleiben erhalten.

## Gezielte Regressionstests

- Exakte Schreibweise beider Anzeigenamen.
- Migration der beiden bekannten R160-Namen.
- Migration älterer automatisch erzeugter Platzhalternamen.
- Keine Migration individueller Namen wie `Mein Tagesverbrauch` oder `PV-Ertrag heute`.
- Tageswertanstieg, persistente Tagesbasis, Teil-Tageskennzeichnung und `total_increasing` bleiben durch die vorhandenen R160-Tests abgedeckt.

## Grenzen

Die tatsächliche Entity-Registry-Migration und Anzeige muss nach Installation in Home Assistant visuell geprüft werden. Die Build-Umgebung enthält keine laufende Home-Assistant-Instanz. Der Registry-Update-Aufruf ist durch Quellcode-Regressionstests abgesichert, aber nicht live ausgeführt.

## Prüfergebnisse R161

- Pytest-Gesamtsuite: **547 bestanden**.
- Python-Syntax/Kompilierung: 134 Python-Dateien erfolgreich kompiliert.
- JavaScript-Syntax: `node --check` erfolgreich.
- JSON: 5 Dateien erfolgreich geparst.
- Übersetzungsstruktur: Deutsch/Englisch jeweils 273 Schlüsselpfade, identisch.
- Paketprüfung: ZIP wird nach Erstellung erneut auf Integrität und vollständige Integrationsstruktur geprüft.

## Nicht live geprüft

Die Entity-Registry-Migration wurde durch gezielte Regressionstests auf bekannte R160-Namen und den Schutz benutzerdefinierter Namen geprüft. Ob Home Assistant den neuen Anzeigenamen nach dem Upgrade tatsächlich in der Geräteansicht rendert, muss im Zielsystem kontrolliert werden.
