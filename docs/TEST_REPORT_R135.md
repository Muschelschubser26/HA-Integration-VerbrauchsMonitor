# Testbericht Beta R135

Datum: 2026-11-26

## Änderungen
- Gesamt geleistete Zahlungen und Gesamt erhaltene Zahlungen werden ausschließlich bei vorhandenen Korrekturen angezeigt. Reihenfolge: Zahlungen, Korrekturen, Gesamtsumme, Saldo/Guthaben.
- Zuverlässigkeit wird nicht mehr durch eine künstliche Mindestwartezeit von 15 Minuten zurückgehalten. Ein deterministischer, datenbasierter Wert wird sofort aus den verfügbaren Eingaben berechnet. Damit ist die 15-Minuten-Grenze keine Wartezeit, sondern die maximale zulässige initiale Berechnungsdauer.
- Abschlagsempfehlung während der Berechnung: „Ein voraussichtlicher monatlicher Abschlag wird gerade berechnet.“
- Release-Metadaten und Frontend-Version auf R135 angehoben.

## Automatisierte Prüfungen
- Python-Unit- und Regressionstests: **463 bestanden**.
- Python-Bytecode-Kompilierung: erfolgreich.
- JavaScript-Syntaxprüfung: erfolgreich.
- JSON-Dateien: erfolgreich validiert.
- Deutsche und englische Übersetzungsstrukturen: synchron.
- ZIP-Integrität: erfolgreich geprüft.

## Nicht durchgeführt
- Kein vollständiger Home-Assistant-Laufzeittest.
- Kein visueller Browser-Test in einer realen Home-Assistant-Instanz.
