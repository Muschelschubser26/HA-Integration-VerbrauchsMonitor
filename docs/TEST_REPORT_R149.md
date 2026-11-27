# Testbericht Beta R149

Datum: 26.11.2026

## Fehlerkorrektur

Der in R148 protokollierte Fehler

`NameError: name 'period_end_date' is not defined`

trat in `ForecastSensor._async_refresh_forecast_value` nach der eigentlichen Prognoseberechnung bei der Ermittlung der Zuverlässigkeits-Kontextabdeckung auf. Die korrekte, zuvor berechnete Periodenendvariable heißt `end_date`. Die fehlerhafte Referenz wurde ersetzt.

Da die Ausnahme vor der Übernahme der Forecast- und Zuverlässigkeitsattribute ausgelöst wurde, konnten die Prognosesensoren ihre Aktualisierung nicht abschließen. Die Korrektur beseitigt diesen konkreten Abbruch für Verbrauch und Einspeisung.

## Regressionstests

- Regressionstest: Periodenendvariable wird in der Refresh-Funktion definiert und verwendet; die alte undefinierte Referenz ist ausgeschlossen.
- Integrationsnaher Berechnungstest: echte `calculate_forecast`-Berechnung, Ableitung der Euro-Einflussgewichte und anschließende Zuverlässigkeitsaggregation ohne historische Vergleiche.
- Historische Daten bleiben optional; der Test bestätigt einen numerischen Wert aus verfügbaren Live-Faktoren und Finanzdaten.
- Veraltete, revisionsgebundene Erwartungen in älteren Regressionstests wurden auf R149 aktualisiert.

## Ergebnisse

| Prüfung | Ergebnis |
|---|---:|
| Pytest | 503 bestanden |
| Python compileall | Bestanden |
| JavaScript `node --check` | Bestanden |
| JSON-Dateien | 5 gültig |
| Übersetzungsschlüssel DE/EN | 189 / 189, vollständig synchron |
| ZIP-Integrität | Nach Erstellung geprüft |

## Nicht durchführbar

Ein vollständiger Home-Assistant-Laufzeittest mit Recorder, echten Entitäten und Neustart konnte in dieser Umgebung nicht ausgeführt werden. Der Test deckt den tatsächlichen Forecast-Berechnungskern und die Zuverlässigkeitsaggregation ab, ersetzt aber nicht die Prüfung der HA-Entity-Lifecycle-Integration in einer laufenden Instanz.
