# Testbericht Beta R134

Datum: 2026-11-26

## Änderungen in R134

- Einspeisungs-Monatsabschlagseditor und Legacy-Reparatur verwenden jetzt dieselbe zentrale Auflösung des vertraglichen Netto-Auszahlungsabschlags.
- Der alte generische `monthly_advance`-Wert wird ausschließlich bei eindeutig einspeisungsbasierten Altverträgen ohne Verbrauchs-Abrechnungsbereich als Legacy-Fallback verwendet. Ein Verbrauchsabschlag wird bei kombinierten Verträgen nicht als Einspeisungsabschlag zweckentfremdet.
- Die Anzeige „derzeit noch nicht zuverlässig berechnet werden“ wurde sprachlich wie abgestimmt ergänzt.
- Der rotierende Ermittlungskreis rotiert jetzt mit 3 Sekunden pro Umdrehung.

## Automatisierte Prüfungen

- Python-Unit-/Regressionstests: 458 bestanden.
- Python-Bytecode-Kompilierung: erfolgreich.
- JavaScript-Syntaxprüfung (`node --check`): erfolgreich.
- JSON-Dateien: 4 gültig.
- Deutsche und englische Übersetzungsstrukturen: Schlüssel synchron.
- ZIP-Integrität und Archivstruktur: separat vor Auslieferung geprüft.

## Gezielte Regressionen

- Feed-in-only Legacy-Vertrag: generischer Monatsabschlag wird als Einspeisungs-Auszahlungsbetrag verwendet.
- Kanonischer `feed_in_monthly_advance` hat Vorrang.
- Bei kombinierten Verbrauchs-/Einspeisungsverträgen wird der Verbrauchsabschlag nicht als Einspeisungsabschlag übernommen.
- Negative oder ungültige Legacy-Beträge werden nicht als gültiger Abschlag verwendet.
- Explizit manuell gespeicherte 0,00 € bleiben erhalten.

## Nicht durchgeführt

- Kein vollständiger Home-Assistant-Laufzeittest.
- Kein visueller Browser-Test innerhalb einer realen Home-Assistant-Instanz.
- Die tatsächlichen Vertragsdaten des Nutzers liegen nicht als Datenbankdatei vor; deshalb konnte nicht verifiziert werden, welcher gespeicherte Vertragswert in seiner Installation vorliegt.

R134 ist damit automatisiert geprüft, benötigt aber weiterhin den praktischen Test in der Home-Assistant-Installation.
