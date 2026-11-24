# Installation und Bedienung – VerbrauchsMonitor 0.0.2 – Beta R113

## Voraussetzungen

- Home Assistant Core 2026.11.1 oder neuer als Projektziel; die konkrete Installation muss im Zielsystem getestet werden.
- Sensorentitäten für die zu verwendenden Zählerstände. Leistungs- und Außenhelligkeitsentitäten sind optional.
- Für saisonale Prognosen geeignete Recorder-Langzeitstatistiken oder ausreichend vorhandene Detailhistorie.

## Manuelle Installation

1. Home-Assistant-Backup erstellen.
2. Den vollständigen Ordner `custom_components/verbrauchsmonitor/` nach `/config/custom_components/verbrauchsmonitor/` kopieren. Einen vorhandenen Ordner vollständig ersetzen.
3. Home Assistant vollständig neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** die Integration **VerbrauchsMonitor** auswählen.
5. Die Ersteinrichtung im Config Flow abschließen.
6. Weitere Verträge, Zähler, Abrechnungen, Buchungen und Prognosen über **Konfigurieren** im Options Flow verwalten.

## Lovelace-Karte

Im Storage-Modus registriert die Integration die Kartenressource automatisch. Danach Dashboard/Browser neu laden und im Kartenpicker nach **VerbrauchsMonitor** suchen. Im YAML-Ressourcenmodus folgende Ressource vom Typ `module` eintragen:

`/verbrauchsmonitor/verbrauchsmonitor-card.js`

Pro logischem Zähler und Abrechnungsrichtung (Verbrauch oder Einspeisung) wird eine eigene Karteninstanz angelegt.

## Konfigurierbare Daten

- Verträge mit Vertragsdaten, Beginn/Ende und Abrechnungszeitraum.
- Netto-/Brutto-Tarife, Mehrwertsteuersatz einschließlich 0 %, Grundpreis und monatliche Abschläge.
- Logische Zähler mit optionaler Zählernummer und optionalen Quellentitäten für Verbrauch, Einspeisung und Leistung.
- Anfangszählerstände mit Herkunft und Datum sowie Routineübernahme an Periodengrenzen.
- Sonderzahlungen, Gutschriften und Korrekturbuchungen je Zähler und Abrechnungsrichtung.
- Monatsabschläge und getrennt aktivierbare Verbrauchs-/Einspeiseprognosen.

## Automatische Monatsabschläge

Jeder Monatserste innerhalb des Abrechnungszeitraums gilt automatisch als Zahlung des vereinbarten Monatsabschlags. Es ist keine manuelle Zahlungsbestätigung erforderlich. Eine explizite, zugeordnete Abschlagsbuchung ersetzt den automatischen Betrag desselben Monats. Verbrauch und Einspeisung werden getrennt geführt. Zukünftige Monatserste zählen nicht zum aktuellen Kontostand, sondern nur als erwartete Zahlung in der Prognose.

## Prognose

Die Prognose wird je Quellzähler und Abrechnungsrichtung verwaltet. Langzeitstatistiken werden bevorzugt; vorhandene Detailhistorie kann als Fallback dienen. Unter 12 Monaten belastbarer Historie wird linear prognostiziert. Ab ausreichender Historienlänge kann ein saisonales Monatsprofil verwendet werden; für längere Vergleiche werden Daten aus zwei Kalenderjahren und Mindestabdeckung vorausgesetzt. Bei unzureichender Datenqualität bleibt die lineare Methode aktiv. Die Jahreszeit wird astronomisch aus den Home-Assistant-Koordinaten ermittelt.

Die Prognose erzeugt keine Zahlungsbuchungen und verändert keinen aktuellen Kontostand.

## Update- und Neustartverhalten

- Vollständiger Austausch des Integrationsordners und danach vollständiger Home-Assistant-Neustart für Python-/Manifeständerungen.
- Dashboard-/Browser-Reload für reine JavaScript-/CSS-Änderungen.
- Änderungen über den Options Flow lösen den vorgesehenen Config-Entry-Reload aus.

Vor Updates mit Datenbank- oder Migrationsänderungen ein Home-Assistant-Backup erstellen.

## Grenzen

Ein erfolgreicher automatisierter Testlauf bestätigt nicht den Start-/Reload-/Unload-Betrieb in der konkreten Home-Assistant-Installation. Recorder-Daten, reale Quellentitäten, Migrationen und Dashboard-Darstellung müssen im Zielsystem geprüft werden. Weitere bekannte Grenzen stehen in `OFFENE_PUNKTE.md`.
