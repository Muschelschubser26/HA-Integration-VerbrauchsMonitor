# Testbericht – Beta R145

## Änderungen

- Die Monatsauswahl für Abschlagsänderungen beginnt weiterhin im Folgemonat und bietet sieben aufeinanderfolgende Kalendermonate. Die Auswahl darf über das Ende des aktuell laufenden Abrechnungszeitraums hinausgehen.
- Beim Speichern wird anhand des Vertragsstarts und der konfigurierten Periodendauer der Abrechnungszeitraum ermittelt, in den der ausgewählte Gültigkeitsmonat fällt. Der neue Betrag wird ab diesem Monat bis zum Ende genau dieses Abrechnungszeitraums gespeichert.
- Ist noch kein belastbarer Zuverlässigkeitswert verfügbar, wird während der ersten 15 Minuten der Initialisierung `forecast_reliability_pending` gesetzt. Die Karte zeigt damit „Zuverlässigkeit: wird ermittelt“ samt animiertem Kreis. Ein vorhandener gültiger Prozentwert wird sofort angezeigt. Nach 15 Minuten wird kein künstlicher Prozentwert erzeugt, wenn tatsächlich keine Bewertungsgrundlage existiert.

## Automatisierte Prüfungen

- Pytest: **493 bestanden**.
- Python-Kompilierung: bestanden.
- JavaScript-Syntaxprüfung (`node --check`): bestanden.
- JSON-Dateien: 4 Dateien gültig.
- Deutsch/Englisch: 189 Schlüsselpfade je Sprache, identisch.

## Nicht durchgeführte Prüfungen

Ein vollständiger Laufzeittest in einer gestarteten Home-Assistant-Instanz wurde nicht durchgeführt. Insbesondere die reale Darstellung des Selectors im HA-Optionsflow, das Speichern über einen echten Vertragsperiodenwechsel, der Neustartablauf und die Animation im tatsächlichen Dashboard müssen dort abschließend geprüft werden.
