# Zuverlässigkeit und langfristige Prognosebewertung

## Grundsatz und Anzeige

Die Karte zeigt höchstens einen Zuverlässigkeits-Prozentwert. Es werden keine zusätzlichen Home-Assistant-Entitäten angelegt. Verbrauch und Einspeisung werden getrennt bewertet.

Die Zuverlässigkeit ist eine evidenzbasierte Einschätzung der verfügbaren Prognosegrundlage. Sie ist keine Garantie für eine spätere Abrechnung und darf nicht mit einer bereits vollständig gemessenen Prognosegenauigkeit verwechselt werden.

## Aktuelle Bewertungsgrundlage

Die aktuelle historische Bewertungsfunktion benötigt eine nutzbare Recorder-Historie mit mindestens:

- 12 Monaten Historienumfang,
- mindestens zwei verwertbaren Stichproben,
- mindestens 50 % Datenabdeckung.

Bei ausreichender Grundlage fließen Historienlänge, Datenabdeckung, maximale Lücken zwischen Datenpunkten, Plausibilität der Historie und die verwendete Prognosemethode in die Bewertung ein. Es wird kein künstlicher Mindestwert addiert. Ohne ausreichende Datenbasis bleibt der Prozentwert nicht verfügbar.

## Prognose-/Ist-Vergleiche

Abgeschlossene stündliche Prognosen und tatsächliche Recorder-Messwerte bilden eine zusätzliche Grundlage für die langfristige Kalibrierung. Historische Prognosen werden nicht nachträglich erfunden. Die belastbare Bewertung tatsächlicher Prognosegenauigkeit setzt echte, zeitlich passende Prognose-/Ist-Paare voraus.

Die laufende Kalibrierung über längere Zeiträume muss im realen Betrieb weiter beobachtet werden. Die initiale Bewertung aus der Qualität der Recorder-Historie ist ausdrücklich nicht dasselbe wie eine statistisch nachgewiesene Prognosegenauigkeit.

## Finanzielle Prognosequalität

Tarif-, Abrechnungs- und Buchungsdaten bilden den fachlichen Kontext der finanziellen Prognose. Ihre bloße Vollständigkeit ist kein Nachweis für die Richtigkeit einer finanziellen Prognose. Ein eigenständiger, belastbarer Finanz-Prognose-/Abrechnungsvergleich bleibt ein offener Entwicklungspunkt und wird nicht als gemessene Prognosegenauigkeit ausgegeben.

## Optionale Umgebungsdaten

Optionale Umgebungsentitäten können als Prognosekontext konfiguriert werden. Fehlende oder ungültige Werte werden ausgelassen. Ihre bloße Konfiguration erzeugt keinen Zuverlässigkeitsbonus. Die Sonnenposition wird lokal aus Home-Assistant-Standort und Zeit berechnet.

## Grenzen und erforderliche Laufzeitprüfung

Die Bewertung hängt von der tatsächlich verfügbaren Recorder-Historie und deren Qualität ab. Lücken oder fehlende Langzeitstatistiken können die Bewertung verhindern oder einschränken.

Vor einer uneingeschränkten Produktionsfreigabe müssen im Zielsystem insbesondere Recorder-Historie, Neustartverhalten, Entity-Registry-Migrationen und die Darstellung im echten Home-Assistant-Frontend praktisch geprüft werden. Siehe `OFFENE_PUNKTE.md`.
