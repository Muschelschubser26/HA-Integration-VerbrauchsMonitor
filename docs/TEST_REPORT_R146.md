# Testbericht – VerbrauchsMonitor Beta R146

## Änderungen

- Abschlagsänderungen werden im Dialog als echte Betragsübergänge behandelt. Identische, für Folgemonate gespeicherte Werte erzeugen keine wiederholten Vormerkhinweise. Nach Inkrafttreten des Betrags wird der Hinweis unterdrückt; eine spätere abweichende Änderung bleibt sichtbar.
- Modul A und B erhalten monetäre Einflussgewichte aus den tatsächlich berechneten Energie- und Grundpreis-/Buchungswerten. Damit kann eine Bewertung ohne historische Prognosevergleiche erfolgen, wenn aktuelle Mess- und Finanzdaten verfügbar sind.
- Die historische Vergleichsbewertung bleibt optional und wird erst ab 24 gültigen Stundenvergleichen einbezogen.
- Während der Initialisierung wird der vereinbarte Status mit animiertem Ladekreis angezeigt. Ein vorhandener Prozentwert wird unmittelbar angezeigt. Ohne Bewertungsgrundlage wird kein künstlicher Wert erzeugt.
- Dashboard-Text „Ø im Monat“ aktualisiert.

## Automatisierte Prüfungen

- Pytest: **495 bestanden**.
- Python-Kompilierung: bestanden.
- JavaScript-Syntaxprüfung (`node --check`): bestanden.
- JSON-Validierung: wird im Auslieferungslauf erneut geprüft.
- Übersetzungsstruktur DE/EN: wird im Auslieferungslauf erneut geprüft.
- ZIP-Integrität und Archivstruktur: wird im Auslieferungslauf erneut geprüft.

## Gezielte Regressionstests

- Dezember 2026: Januar 2027 mit 220,00 € wird als nächste Änderung angezeigt.
- Januar 2027: der aktive Betrag 220,00 € wird nicht erneut als Vormerkung für Februar angezeigt.
- März 2027: eine abweichende Änderung auf 250,00 € bleibt als nächste Änderung sichtbar.
- Nach März 2027: identische Fortführungsdatensätze erzeugen keinen Hinweis.
- Zuverlässigkeit mit aktuellen Mess-/Finanzfaktoren und ohne Historie liefert einen reproduzierbaren Prozentwert.

## Nicht durchgeführte Prüfungen

Ein vollständiger Home-Assistant-Laufzeittest wurde nicht durchgeführt. Die reale Darstellung des Dialogs, die Datenbankpersistenz im laufenden HA-System, Neustartverhalten und die Animation müssen zusätzlich in einer gestarteten Home-Assistant-Instanz geprüft werden.
