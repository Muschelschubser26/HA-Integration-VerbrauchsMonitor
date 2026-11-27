# Testbericht VerbrauchsMonitor Beta R159

## Umfang

- Zuverlässigkeitsbewertung: konservativere zeitliche Gewichtung, explizite Konfidenz der initialen Recorder-Evidenz und getrennte Datenbasis für Verbrauch/Einspeisung.
- Prognoseabweichung: energiegewichteter Fehler mit zusätzlicher Horizontgewichtung, damit sehr kleine bzw. nächtliche Nullwerte die Kennzahl nicht dominieren und kurzfristige Prognosen stärker zählen; Alt-Datensätze ohne kWh-Paare bleiben kompatibel.
- Tageswertsensoren: Migration bekannter Registry-Kurzbezeichnungen und Prüfung der steigenden Tagesdifferenz einschließlich Tagesreset.
- Keine zusätzlichen Home-Assistant-Entitäten und keine Änderung an Abrechnungs-/Zahlungslogik.

## Automatisierte Prüfungen

- Pytest: 539 Tests bestanden.
- Python-Bytecode-Kompilierung: durchgeführt.
- JavaScript-Syntaxprüfung: durchgeführt.
- JSON-Dateien: alle Dateien im Projekt gültig.
- Deutsche und englische Übersetzungsdateien: JSON gültig und synchroner Schlüsselbestand.
- ZIP-Integrität und vollständige Projektstruktur: geprüft.

## Gezielte Regressionstests R159

- Initiale hohe Historienqualität wird durch die Evidenz-Konfidenz und den zeitlichen Faktor konservativ bewertet.
- Unterschiedliche Verbrauchs-/Einspeisungshistorien ergeben unterschiedliche Anfangswerte; keine gemeinsame pauschale 92-%-Deckelung erzeugt künstlich identische Werte.
- Energiegewichteter Fehler wird an einer Reihe mit vielen Null-Einspeisestunden geprüft.
- Ältere gespeicherte Evaluierungen ohne tatsächliche/prognostizierte kWh-Felder bleiben lesbar.
- Der Prognosehorizont wird in neuen Vergleichen gespeichert; kurzfristige Prognosen erhalten ein höheres Gewicht als weit vorausreichende Prognosen.
- Tageswertdifferenz steigt mit dem Quellzähler, wird bei neuem Tagesbaselinewert null und liefert bei rückläufigem Zähler keinen negativen Wert.
- Bekannte Registry-Platzhalter werden korrigiert; explizite manuelle Namen werden nicht überschrieben.

## Nicht durchführbare Laufzeitprüfungen

Ein vollständiger Home-Assistant-Laufzeittest mit der tatsächlichen Recorder-Datenbank, der echten Entity Registry, realen Zählerwechseln und dem Langzeitstatistik-Subsystem war in dieser Umgebung nicht möglich. Diese Punkte bleiben für den Test im Zielsystem offen. Automatisierte Tests sind kein Ersatz für diesen Praxistest.
