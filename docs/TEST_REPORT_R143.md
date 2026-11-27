# Testbericht – Beta R143

## Ergebnis

- Automatisierte Tests: 483 bestanden.
- Python-Kompilierung: erfolgreich (`compileall`).
- JavaScript-Syntax: erfolgreich (`node --check`).
- JSON-Dateien: 5 gültig.
- Übersetzungen: 189 Schlüsselpfade in Deutsch und Englisch, vollständig synchron.
- ZIP-Integrität: wird nach Archivierung geprüft.

## Geprüfte Änderungen

- Künstlicher Zuverlässigkeitsstartwert einschließlich Basis 28 entfernt; der alte gespeicherte Startwert wird nicht mehr geladen.
- Modulbeiträge ohne explizites Einflussgewicht werden ausgeschlossen.
- Verfügbare Live-Evidenz wird sofort ausgewertet; bei fehlender Bewertungsgrundlage wird kein Prozentwert erfunden und kein endloser Ladeindikator angezeigt.
- Historische Prognosevergleiche werden erst ab 24 gültigen Stundenwerten berücksichtigt.
- Tarifanzeige auf zwei Nachkommastellen begrenzt; interne Dezimalberechnung bleibt unverändert.
- Doppelte Gesamtzahlungszeilen entfernt; Einspeisung bezeichnet den Gesamtbetrag als „Gesamt erhaltene Zahlungen“.

## Nicht durchgeführte Prüfung

Ein vollständiger Home-Assistant-Laufzeittest (einschließlich Neustart, Recorder, mehrere Verträge/Zähler und Live-Datenänderungen) wurde nicht durchgeführt. Die 15-Minuten-Grenze wird nicht durch einen Timer erzwungen: verwertbare Evidenz wird beim ersten Forecast-Refresh sofort ausgewertet. Ohne irgendeine Bewertungsgrundlage bleibt ein Prozentwert fachlich unmöglich und wird nicht künstlich erzeugt.


R143 ergänzt Zahlungs-/Kontostandsregressionen: gruppierte Monatsabschläge werden als bis zum aktuellen Monat gezahlt berücksichtigt; Korrekturen stehen vor der fett dargestellten Gesamtzahlung. Beispiel: 800,00 € − 66,00 € − 606,38 € = 127,62 € Guthaben.
