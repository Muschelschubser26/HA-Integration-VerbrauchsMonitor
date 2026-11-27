# Testbericht R141

Stand: 26.11.2026

## Änderungen
- Vorgemerkte Abschläge vollständig aus der Dashboard-Zahlungsübersicht entfernt.
- Abgelaufene Monate werden gemäß der festgelegten Projektregel als gezahlte Monatsabschläge angesetzt.
- Monatsgruppen folgen der effektiven Betragshistorie: Einzelmonat ohne Multiplikator; zusammenhängende gleiche Beträge werden zusammengefasst.
- Gesamt geleistete Zahlungen wird immer dargestellt; Sonderzahlungen und Korrekturen werden in die Gesamtsumme einbezogen.
- Historische Zuverlässigkeitsvergleiche werden erst ab 24 gültigen Vergleichen berücksichtigt.

## Automatisierte Prüfungen
- Pytest: 484 bestanden.
- Python-Kompilierung: bestanden.
- JavaScript-Syntax: bestanden.
- JSON-Validierung: alle JSON-Dateien erfolgreich geladen.
- Home-Assistant-Laufzeittest: nicht durchgeführt.

## Fachlicher Hinweis
Die Einstufung jedes bereits begonnenen Monats als gezahlter Abschlag folgt ausdrücklich der zuletzt bestätigten Projektvorgabe. Sie ist eine fachliche Abrechnungsannahme der Integration und kein Nachweis eines externen Zahlungsvorgangs.
