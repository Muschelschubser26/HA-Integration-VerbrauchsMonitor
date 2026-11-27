# Testbericht Beta R151

## Umfang
- Zuverlässigkeit basiert ausschließlich auf realen Stundenprognose-/Messwertvergleichen.
- Mindestens 24 gültige Vergleiche erforderlich.
- Zeitlicher Fortschritt des Abrechnungszeitraums skaliert die gemessene Genauigkeit; er kann sie nicht erhöhen.
- Obergrenzen: regulär 92 %, in den letzten 24 Stunden 94 %, in der letzten Stunde 95 %.
- Bis zu drei Jahre abgeschlossene Stundenvergleiche; Modellanpassung separat mit aktuellem 90-Tage-Fenster und Holdout-Prüfung.
- Keine zusätzlichen Home-Assistant-Entitäten.

## Automatisierte Prüfungen
- Python-Bytecode-Kompilierung: erfolgreich.
- Pytest: 511 Tests bestanden.
- JSON-Syntax: 4 JSON-Dateien gültig.
- Deutsche/englische Übersetzungspfade: 194/194, vollständig synchron.
- JavaScript-Syntaxprüfung der Lovelace-Karte (`node --check`): erfolgreich.
- Regressionen für fehlende Evidenz, Initialisierungsanzeige, 24-Stunden-Mindestbasis, zeitliche Obergrenzen und 95-%-Freigabe in der letzten Stunde: erfolgreich.
- ZIP-Integritätsprüfung und Vollständigkeit: nach Archiv-Erstellung dokumentiert.

## Nicht durchführbar in dieser Umgebung
- Kein vollständiger Home-Assistant-Laufzeittest.
- Keine Prüfung mit realen Recorder-Daten, echten Zählerverläufen oder einer produktiven Abrechnung.
- Langfristige Verbesserung über mehrere Monate/Jahre kann erst nach entsprechendem Betrieb mit realen Daten empirisch bestätigt werden.
- Ein eigenständiger Abgleich historischer Zuverlässigkeits-Prozentwerte gegen spätere tatsächliche Genauigkeit sowie ein finanzieller Prognose-/Abrechnungsvergleich sind noch nicht als vollständige Kalibrierungsstrecke umgesetzt. Das Finanzmodul wird deshalb bis dahin nicht in die Prozentaggregation aufgenommen.
- Auslieferungsarchiv `Integration-VerbrauchsMonitor-0.0.2-Beta-R151.zip`: 172 Dateien, erwarteter Integrationsordner als ZIP-Wurzel, `ZipFile.testzip()` ohne Fehler.
