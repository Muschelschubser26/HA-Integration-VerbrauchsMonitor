# Kalenderbezogene Energie-Sensoren

## Zeitliche Abgrenzung

Die Periodensensoren verwenden die lokale Home-Assistant-Zeit. Wochen beginnen am Montag (ISO-Kalenderwoche), Monate am ersten Kalendertag und Jahre am 1. Januar. Der Wechsel wird einmal täglich um 00:00:05 Uhr geprüft. Beim Start und bei jeder gültigen Quellmesswertänderung wird zusätzlich der gespeicherte Periodenschlüssel abgeglichen.

## Ressourcenschonung

Es gibt keine minütliche Polling-Schleife. Die Zeitprüfung ist auf einen Aufruf pro Tag je Periodensensor begrenzt. Messwertänderungen werden ereignisgesteuert verarbeitet. Ein Periodenwechsel speichert nur den betroffenen Sensorzustand.

## Fehlender Messwert am Wechsel

Ein fehlender oder ungültiger Quellwert um Mitternacht löscht die vorhandene Referenz nicht und setzt den Sensor nicht allein deshalb auf nicht verfügbar. Der nächste gültige Messwert erkennt den abweichenden Periodenschlüssel und startet einen gekennzeichneten Teilzeitraum. Damit wird kein Verbrauch erfunden. Wenn zwischen dem letzten gültigen Messwert vor der Grenze und dem ersten danach Energie verbraucht wurde, kann diese mangels Messpunkten nicht exakt auf die beiden Perioden verteilt werden; der Zeitraum wird daher als teilweise erfasst gekennzeichnet.

## Persistenz und Neustart

Baseline, Periodenschlüssel, Zählerwechsel-Offset und letzter gültiger Messwert werden im Home-Assistant-Store je Zähler und Richtung gespeichert. Beim Start wird der aktuelle Periodenschlüssel mit dem gespeicherten Schlüssel verglichen. Wenn er abweicht, wird die bestehende Recorder-Rekonstruktion versucht; ist keine belastbare historische Referenz verfügbar, beginnt ein ausdrücklich gekennzeichneter Teilzeitraum mit dem ersten gültigen Messwert.

## Grenzen der Validierung

Automatisierte Tests prüfen Codepfade und Regressionen. Ein realer Home-Assistant-Laufzeittest mit Recorder-Daten, HA-Neustart exakt um Mitternacht, Messlücke und physischem Zählerwechsel ist vor einer produktiven Langzeitnutzung weiterhin erforderlich.


## Gezielter Reset der Periodenwerte (R168)

Unter Datenverwaltung → Einzelne Datenbereiche zurücksetzen kann zusätzlich „Reset der Periodenwerte“ gewählt werden. Im Folgeschritt werden alle konfigurierten Zähler und verfügbaren Energierichtungen einzeln angeboten. Eine Auswahl gilt immer gemeinsam für Tag, Woche, Monat und Jahr dieser Zählerrichtung. Verbrauch und Einspeisung sind getrennte Auswahlbereiche.

Vor dem Speichern werden alle ausgewählten Quellzustände auf Verfügbarkeit und gültige, endliche, nichtnegative Zählerstände geprüft. Erst danach werden die vier zugehörigen Home-Assistant-Store-Referenzen auf den aktuellen kumulativen Zählerstand gesetzt. Die Perioden starten damit ab dem Resetzeitpunkt; die Werte werden als Teilzeitraum gekennzeichnet. Historische Zählerwechsel-Segmente, Verträge, Tarife, Buchungen, Abrechnungen und die SQLite-Datenbank werden nicht gelöscht. Vor dem Schreiben wird eine dauerhafte Sicherung der vorherigen Perioden-Store-Inhalte erstellt. Bei einem Speicherfehler wird versucht, bereits geschriebene Store-Dateien auf ihren vorherigen Inhalt zurückzusetzen. Nach erfolgreicher Bestätigung erzwingt eine interne Options-Generation den Reload der Sensorobjekte, damit die neuen Referenzen unmittelbar eingelesen werden.
