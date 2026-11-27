# Testbericht – VerbrauchsMonitor Beta R139

**Basis:** vom Benutzer bereitgestellter Beta-R137-Quellstand  
**Version:** 0.0.2  
**Revision:** R139  
**Datum:** 26.11.2026

## Änderungen

- Neue Backend-Komponente `reliability.py` mit offener Modulregistrierung und zentraler Aggregation.
- Modul A bewertet die Prognosequalität (Verbrauch/Einspeisung); abgeschlossene stündliche Prognose-Ist-Vergleiche fließen ab fünf Datensätzen ein.
- Modul B bewertet verfügbare finanzielle Eingaben (Tarif, Abrechnungszeitraum, Grundpreis, tatsächlich vorhandene Buchungen und zukünftige Abschlagsplanung).
- Die Module liefern interne Einzelbeiträge; nach außen wird nur eine Gesamtzuverlässigkeit in Prozent ausgegeben.
- Die Gewichtung wird über die jeweiligen prognostizierten Euro-Auswirkungen gespeist, soweit diese Werte vom Prognoseergebnis geliefert werden. Fehlt ein solcher Betrag, wird für den vorhandenen Modulbeitrag ein neutraler Gewichtungsfallback von 1 verwendet.
- Fehlende Messhistorie wird nicht als negativer Faktor eingerechnet. Sie wird erst über echte Prognose-Ist-Vergleiche berücksichtigt.
- Künstliche Mindestwerte und zufällige Startwerte wurden entfernt. Prozentwerte unter 10 % sind zulässig.
- Weitere Module können unter beliebigen Schlüsseln registriert werden; keine feste Begrenzung auf A/B/C/D.

## Automatisierte Prüfungen

| Prüfung | Ergebnis |
|---|---|
| Pytest-Testsuite | **479 bestanden** |
| Python-Kompilierung (`compileall`) | **Bestanden** |
| JavaScript-Syntax (`node --check`) | **Bestanden** |
| JSON-Validierung aller JSON-Dateien | **Bestanden** |
| Schlüsselparität DE/EN | **Bestanden** |
| Regression: fehlende Historie wird ausgelassen | **Bestanden** |
| Regression: Erweiterung um beliebige Module | **Bestanden** |
| Regression: keine künstliche Untergrenze / Werte < 10 % | **Bestanden** |
| Regression: deterministische Ergebnisse | **Bestanden** |
| Regression: getrennte Verbrauchs-/Einspeisungs-Lernspeicher | Durch bestehende Tests abgedeckt; keine vollständige HA-Laufzeitprüfung |

## Einschränkungen / offene Prüfung

- Ein vollständiger Home-Assistant-Laufzeittest war in dieser Umgebung nicht möglich. Insbesondere müssen Recorder-Datenzugriff, Neustartverhalten, reale Zustandsattribute und die Darstellung in der Lovelace-Karte in der Zielinstallation geprüft werden.
- Die A/B-Gewichtung verwendet die vom Prognoseergebnis verfügbaren Euro-Komponenten. Wo diese nicht verfügbar oder null sind, greift der dokumentierte neutrale Gewichtungsfallback. Für eine spätere fachliche Verfeinerung sollte die finanzielle Sensitivität der Prognose anhand expliziter Kosten-/Erlös-Szenarien validiert werden.
- A und B bewerten derzeit die Verfügbarkeit/Qualität der aktuell bereitgestellten Faktoren und vorhandene Prognose-Ist-Abweichungen. Saison, Sonnenstand und Tageszeit werden als verfügbare Prognosekontexte berücksichtigt; ihre statistische Güte wird nicht als bereits empirisch validiert ausgegeben.

## Ergebnis

Die automatisierten Prüfungen sind erfolgreich. R139 ist als vollständiges Beta-Paket erstellt. Die genannten Home-Assistant-Laufzeit- und fachlichen Validierungen bleiben vor einer Produktionsübernahme erforderlich.
