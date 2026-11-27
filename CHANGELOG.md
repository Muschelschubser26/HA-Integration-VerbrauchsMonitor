## 0.0.2 Beta R171 – 27.11.2026

- Datenbankinformationen zeigen den dynamischen vollständigen Pfad einschließlich Dateiname an.
- Leerzeile zwischen Datenbankpfad und Statusinformationen ergänzt.
- Leerzeile zwischen Buchungsanzahl und letzter Änderung ergänzt.
- Keine Änderung an Datenbankschema, Datenbestand oder Optimierungsverhalten.

## 0.0.2 Beta R170 – 27.11.2026

- Korrigiert alle Recorder-Abfragen in `sensor.py`: Langzeitstatistiken und detaillierte Historie laufen über `get_instance(hass).async_add_executor_job()` statt über den allgemeinen Home-Assistant-Executor.
- Belässt CPU-intensive Prognoseberechnungen im allgemeinen Executor; diese sind keine Recorder-Datenbankzugriffe.
- Ignoriert fehlende, `unknown` und `unavailable` Quellzustände während Start/Reload vor der Messwertvalidierung. Diese transienten Zustände verändern keine Referenz und erzeugen keine Warnungsflut.
- Behält die strenge Validierung und Protokollierung tatsächlich fehlerhafter numerischer Messwerte sowie unzulässiger Zählerstands-Rückgänge bei.
- Ergänzt Regressionstests für Recorder-Executor-Verwendung und transiente Quellzustände.

## 0.0.2 Dev R169 – 27.11.2026

- Ergänzt eine migrationssichere SQLite-Schemaerweiterung von Version 1 auf Version 2 mit Vor-Migrationssicherung, getrennten fachlichen Tabellen, relationalen Zuordnungsspalten und Fremdschlüsseln. Die vollständige Snapshot-Payload bleibt als Kompatibilitäts- und Wiederherstellungsgrundlage erhalten.
- Synchronisiert Konfigurationen von Verträgen und logischen Zählern zusätzlich aus den Config-Entry-Optionen in die SQLite-Projektion; die Optionen bleiben vorerst führend.
- Ergänzt zentrale strenge Messwertvalidierung. Ungültige, nicht endliche, negative oder rückläufige Werte überschreiben keine gespeicherten Referenzen. Rückläufige Werte werden nur bei dokumentiertem Zählerwechsel mit gültigem Endstand akzeptiert.
- Ergänzt unabhängiges Prognosemodell 3 – Kalender-Jahreszeitenmodell – und die gewichtete Kombination verfügbarer Prognosemodelle. Fehlende saisonale Daten werden nicht als Nullwerte interpretiert.
- Ändert die Kartenbeschriftung „Bereits gezahlt:“ in „Bereits bezahlt:“ und die englische Beschriftung in „Already paid:“.
- Bewahrt die vorhandene Speicherung der Tages-, Wochen-, Monats- und Jahreswerte unverändert. Keine Löschung historischer Periodenwerte.
- Ergänzt Regressionstests für Migration, Vor-Migrationssicherung, Fremdschlüssel, Messwertvalidierung und das dritte Prognosemodell.

## 0.0.2 Beta R168 – 27.11.2026

- Korrigiert den Periodenreset: Nach dem Schreiben der vier Referenzspeicher wird eine geänderte interne Reset-Generation in den Optionen gespeichert. Dadurch wird der Config-Entry auch dann neu geladen, wenn keine sichtbare Option geändert wurde; die Sensorobjekte lesen die neuen Referenzen erneut ein.
- Sichert die vorherigen Perioden-Store-Inhalte dauerhaft in einem separaten Home-Assistant-Store, bevor Referenzen überschrieben werden; Schreibfehler lösen weiterhin einen Rollback aus.
- Ersetzt die pauschale Abhängigkeitsmeldung durch eine Prüfung mehrfach verwendeter Quell-Entitäten in den konfigurierten Zählerzuordnungen.
- Korrigiert den Bestätigungstext: Gesichert werden die Periodenreferenzen, nicht pauschal die SQLite-Datenbankdatei.
- Ergänzt Regressionstests für Store-Schlüssel, Reset-Generation, Backup und Mehrfachzuordnungen.

## 0.0.2 Beta R167 – 27.11.2026

- Ergänzt unter „Einzelne Datenbereiche zurücksetzen“ den Bereich „Periodenwerte zurücksetzen“ mit direktem Folgeschritt zur Auswahl konfigurierter Zähler und Energierichtungen.
- Der Reset setzt Tag, Woche, Monat und Jahr je ausgewählter Zählerrichtung auf den aktuellen kumulativen Quellzählerstand; nicht konfigurierte Einspeisungen werden nicht angeboten.
- Alle ausgewählten Quellwerte werden vor dem ersten Schreibvorgang geprüft. Bei nicht verfügbaren oder ungültigen Messwerten wird der Reset abgebrochen.
- Die Perioden-Stores werden gezielt aktualisiert; Verträge, Tarife, Buchungen, Abrechnungen und physische Zählerwechsel-Historie werden nicht gelöscht.
- Deutsche und englische Dialogtexte sowie Regressionstests für den neuen Ablauf ergänzt.

## 0.0.2 Beta R166 – 26.11.2026

- Periodenwechsel werden ressourcenschonend einmal täglich um 00:00:05 Uhr lokaler Home-Assistant-Zeit geprüft; zusätzlich erfolgt beim Start bzw. bei der ersten gültigen Messwertaktualisierung ein Abgleich des gespeicherten Periodenschlüssels.
- Fehlende Zählerwerte genau zum Mitternachtszeitpunkt setzen die Zeitraum-Sensoren nicht mehr auf „nicht verfügbar“ und löschen keine Referenzstände. Der erste spätere gültige Messwert eröffnet einen gekennzeichneten Teilzeitraum.
- Ergänzt Wochenverbrauch und Wocheneinspeisung je konfigurierter Messrichtung; Wochenbeginn ist Montag gemäß ISO-Kalenderwoche. Monats- und Jahreswerte bleiben erhalten.
- Keine minütliche Dauerprüfung und keine zusätzlichen Timer je Messwert; die Prüfung erfolgt zentral je Sensor nur einmal täglich sowie ereignisbezogen bei neuen Quellmesswerten.
- Neustart- und Messlückenverhalten wird durch zusätzliche Regressionstests abgesichert.

## 0.0.2 Beta R165 – 26.11.2026

- Ergänzt je konfigurierter Verbrauchs- und Einspeiserichtung eigene Sensoren für Tages-, Monats- und Jahresenergie. Monats- und Jahreswerte verwenden lokale Kalendergrenzen und persistente Referenzstände.
- Monats-/Jahresbasen werden nach Neustarts aus dem Home-Assistant-Store wiederhergestellt und bei fehlender passender Basis soweit möglich aus Recorder-Historie rekonstruiert; andernfalls wird ein ausdrücklich gekennzeichneter Teilzeitraum ab dem ersten verfügbaren Messwert ausgewiesen.
- Rückläufige kumulative Messwerte werden als Zählerreset/-wechsel behandelt: der bis dahin berechnete Abschnitt wird als Offset konserviert und der neue Zählerabschnitt beginnt bei null.
- Recorder-Export listet nur VerbrauchsMonitor-eigene Entitäten, getrennt nach Verbrauch und Einspeisung; externe Quell- und Fremdentitäten werden nicht aufgenommen. Die YAML-Ausgabe verwendet echte Zeilenumbrüche.
- Prognose-Entity-IDs für Jahresbilanzen verwenden deutsche Bezeichnungen; Entity-Registry-Migration behält die vorhandene Unique-ID bei.

## 0.0.2 Beta R164 – 26.11.2026

- Trennt den Hauptmenüpunkt „Abrechnung“ von „Monatsabschlag und Buchungen“ und ordnet beide Bereiche direkt nach „Prognose & Zuverlässigkeit“ ein.
- Benennt den bisherigen Bereich „Abrechnungen und Abschläge“ in „Monatsabschlag und Buchungen“ um; die Reihenfolge lautet „Monatsabschlag ändern“, „Monatsabschläge bearbeiten“, „Buchungen verwalten“.
- Ergänzt den Bereich „Abrechnung“ mit den direkten Navigationspunkten „Abrechnung erstellen“ und „Abrechnung aufrufen“ sowie OK-Schaltflächen in den Ziel-Dialogen. Die eigentliche Abrechnungserstellung und -übersicht sind noch nicht implementiert; die Dialoge bilden zunächst die vereinbarte Navigation ab.

## 0.0.2 Beta R163 – 26.11.2026

- Korrigiert die kanonischen Entity-IDs der Tageswerte auf `*_tagesverbrauch` und `*_tageseinspeisung`; die bestehende Unique-ID bleibt erhalten, sodass die Entity-Registry-Migration die vorhandene Entität umbenennt statt eine neue Identität anzulegen.
- Erweitert die Recorder-Übersicht um beide Tageswerte je konfiguriertem Zähler und ordnet Quellen sowie Tageswerte je Zähler getrennt den Gruppen Verbrauch und Einspeisung zu.
- Formatiert die Include-Ausgabe mit dem VerbrauchsMonitor-Kopfbereich, zusätzlicher `##`-Zeile und `# note:`-Gruppen.
- Entfernt „ca.“ aus der Anzeige „Ø im Monat“.
- Entfernt bei monatlichen Abschlags-/Einnahmenbeträgen ausschließlich innerhalb der Klammern unnötige Nachkommastellen; alle Summen außerhalb der Klammern bleiben unverändert.

## 0.0.2 Beta R162 – 26.11.2026

- Ergänzt unter Datenverwaltung den Menüpunkt „Verwendete Recorder – Entitäten“ mit zwei auswählbaren YAML-Formaten: ohne Einrückung für `recorder.yaml` und mit zwei Leerzeichen Einrückung für eine `include`-Datei. Die Liste wird dynamisch aus den in Home Assistant registrierten Entitäten dieser Integration erzeugt und kann im mehrzeiligen Textfeld markiert und kopiert werden.

## Beta 0.0.2 – R161
- Tageswertsensoren erhalten die gewünschten eindeutigen Anzeigenamen `TagesVerbrauch` und `TagesEinspeisung`; der redundante Zusatz „(heute)“ entfällt.
- Bekannte automatisch erzeugte R160-Namen `Tagesverbrauch (heute)` und `Tages-Einspeisung (heute)` werden bei der Entity-Registry-Migration auf die neuen Namen aktualisiert. Individuelle Benutzerumbenennungen bleiben unangetastet.
- Entity-IDs, Unique-IDs, Tagesbasis, Lernhistorie, Zustandsklasse `total_increasing` und Tageswertberechnung bleiben unverändert.
- Regressionstests prüfen beide exakten Anzeigenamen sowie die Migration der R160-Bezeichnungen und den Schutz individueller Namen.

## Beta 0.0.2 – R159
- Zuverlässigkeitsbewertung überarbeitet: Initiale Recorder-Bewertung wird mit einer expliziten Evidenz-Konfidenz aus Historienlänge, Abdeckung und Stichprobenumfang gewichtet; die Zeitkomponente verwendet eine konservativere Quadratwurzelkurve statt der bisherigen vierten Wurzel. Damit erreicht eine reine Datenqualitätsbewertung nicht vorschnell die 92-%-Obergrenze.
- Verbrauch und Einspeisung bleiben strikt getrennte Bewertungs- und Lernpfade. Unterschiedliche Historienqualität führt zu unterschiedlichen Anfangsbewertungen; identische Werte sind nur noch möglich, wenn die getrennten Belege tatsächlich gleichwertig sind.
- Prognose-Ist-Abweichungen verwenden bei vorhandenen tatsächlichen und prognostizierten kWh-Werten einen energiegewichteten absoluten Prozentfehler. Kleine bzw. nächtliche Null-Einspeisewerte dominieren dadurch die Einspeisungsbewertung nicht. Alte gespeicherte Evaluierungen ohne kWh-Paar bleiben kompatibel.
- Tageswertsensoren korrigieren zusätzlich den alten Registry-Platzhalter über den gespeicherten Originalnamen, sofern kein individueller Benutzername gesetzt ist. Die Namen lauten „Verbrauch (heute)“ und „Einspeisung (heute)“.
- Tageswerte bleiben steigende Tagesdifferenzen aus kumuliertem Zählerstand minus persistenter Tagesbasis; `total_increasing` bleibt die zulässige Energie-Zustandsklasse. Fehlende Tagesbasis wird weiterhin nicht durch einen erfundenen Nullwert ersetzt.
- Keine zusätzlichen Home-Assistant-Entitäten; Kartenlayout, Abrechnungslogik, Lernspeicher und bestehende Entity-IDs bleiben erhalten.

## Beta 0.0.2 – R158
- Zuverlässigkeitsanzeige: Wenn keine ausreichende 12-Monats-Recorder-Historie und noch keine 24 abgeschlossenen Prognose-Ist-Vergleiche vorliegen, wird eine ausdrücklich als initiale Eingangs-/Konfigurationsqualität gekennzeichnete Bewertung aus tatsächlich verfügbaren Messwert-Frische-, Historien- und Tarif-/Abrechnungsdaten berechnet. Fehlende optionale Entitäten werden ausgelassen; es wird kein Mindestwert addiert.
- Tageswertsensoren: Die Korrektur des bekannten Registry-Platzhalters umfasst zusätzlich die HA-Varianten „heute“ und „(today)“, ohne individuelle Umbenennungen zu überschreiben.
- Tagesbasis: Wenn signifikante Recorder-Zustände fehlen, wird die Tagesbasis ersatzweise aus mindestens zwei gültigen kumulativen Langzeitstatistik-Summen des laufenden Tages rekonstruiert. Ohne belastbare Daten bleibt der Tageswert unbekannt statt erfunden.
- Bestehende Entity-IDs, Lernhistorie, Kartenlayout und Abrechnungslogik bleiben erhalten.

## Beta 0.0.2 – R157
- Recorder-Abfragen zur Rekonstruktion der Tagesbasis laufen jetzt über den Recorder-eigenen Executor (`get_instance(hass).async_add_executor_job`) statt über den allgemeinen Home-Assistant-Executor. Dadurch wird der Recorder-Datenbankzugriff integrationskonform ausgeführt.
- Tageswertsensoren verwenden `total_increasing` als zulässige Zustandsklasse für Energie-Entitäten. Der Tagesreset wird als Zählerreset behandelt; fehlende Tagesbasen erzeugen weiterhin keinen erfundenen Wert.
- Ein bekannter fehlerhafter Registry-Anzeigename `(heute)` wird gezielt auf „Verbrauch (heute)“ beziehungsweise „Einspeisung (heute)“ korrigiert. Individuelle Benutzerumbenennungen bleiben erhalten.
- Bestehende Entity-IDs, Tagesbasis-Speicherung, Kartenlayout und Prognosefunktionen bleiben erhalten.

# Changelog

## Beta 0.0.2 – R156
- Behebt die Anzeige „keine Bewertungsgrundlage“ bei vorhandener, ausreichend langer Recorder-Historie: Die vorhandene Historienqualität (Zeitraum, Abdeckung, Kontinuität, Plausibilität und Prognosemethode) liefert jetzt eine nachvollziehbare initiale Zuverlässigkeitsbewertung.
- Diese initiale Bewertung wird ausdrücklich als Recorder-Historienqualität gekennzeichnet und nicht als bereits gemessene Prognosegenauigkeit ausgegeben.
- Sobald mindestens 24 gültige stündliche Prognose-Ist-Vergleiche vorliegen, ersetzen diese die initiale Historienbewertung.
- Zeitlicher Abrechnungsfortschritt und Obergrenzen von 92 %, 94 % beziehungsweise maximal 95 % in der letzten Stunde bleiben unverändert.
- Keine zusätzlichen Home-Assistant-Entitäten; Lernhistorie und R155-Tageswertsensoren bleiben erhalten.


## Beta 0.0.2 – R155
- Neue tägliche Energieentität je konfigurierter Zählerrichtung: „Verbrauch (heute)“ beziehungsweise „Einspeisung (heute)“.
- Tageswerte werden als Differenz des kumulierten Zählerstands zum Tagesbeginn berechnet; Verbrauch und Einspeisung bleiben getrennt.
- Tagesbasis wird je logischem Zähler und Richtung dauerhaft im Home-Assistant-Store gespeichert und nach Neustarts wiederhergestellt.
- Fehlt die gespeicherte Tagesbasis (z. B. bei erstmaliger Installation am laufenden Tag), wird sie soweit möglich aus der Recorder-Historie zum Tagesbeginn rekonstruiert. Ist das nicht möglich, wird kein erfundener Tageswert ausgegeben.
- Bei einem rückläufigen Zählerstand (Reset/Zählerwechsel) wird kein negativer Tagesverbrauch angezeigt.

## Beta 0.0.2 – R154
- Zuverlässigkeitsanzeige ergänzt um den tatsächlichen Fortschritt der Berechnungsphasen: Datenbasis, Prognoseberechnung und Zuverlässigkeitsauswertung. Der Fortschritt ist ausdrücklich unabhängig vom Zuverlässigkeits-Prozentwert.
- Fortschrittswert wird als `(xx %)` zwischen „wird ermittelt“ und dem animierten Symbol angezeigt.
- Fortschritt wird innerhalb der Sensorlaufzeit monoton geführt; zusätzliche Zustandsänderungen können den angezeigten Fortschritt nicht zurücksetzen. Der Spinner bleibt während einer laufenden Neuberechnung aktiv.
- Keine zusätzlichen Home-Assistant-Entitäten; bestehendes R153-Kartenlayout und die fachliche Zuverlässigkeitsberechnung bleiben unverändert.


## Beta 0.0.2 – R151
- Zuverlässigkeit wird nicht mehr aus bloßer Messwert-Aktualität oder vollständigen Tarif-/Finanzdaten abgeleitet; ohne mindestens 24 gültige Prognose-Ist-Vergleiche wird kein Prozentwert ausgegeben.
- Die gemessene Prognosegenauigkeit wird mit dem zeitlichen Fortschritt des Abrechnungszeitraums verknüpft. Die zeitliche Komponente kann die reale Genauigkeit nicht erhöhen.
- Zuverlässigkeitsobergrenze regulär 92 %, in den letzten 24 Stunden 94 % und ausschließlich in der letzten Stunde 95 %; die jeweilige Obergrenze ist kein garantierter Zielwert.
- Abgeschlossene stündliche Vergleiche bleiben bis zu drei Jahre lokal erhalten; die Modellanpassung verwendet weiterhin ein separates aktuelles 90-Tage-Fenster mit Holdout-Prüfung.
- Keine zusätzlichen Home-Assistant-Entitäten. Finanzielle Zuverlässigkeit wird erst aggregiert, wenn echte Prognose-/Abrechnungsergebnisse vergleichbar vorliegen.
- Regressionstests für Zeitfaktor, 95-%-Grenze, fehlende Evidenz und Langzeitspeicherung ergänzt.

## Beta 0.0.2 – R150
- Konfigurationsnavigation und Dialogtitel auf „Prognose & Zuverlässigkeit“ umbenannt.
- Fünf optionale Wetter-/Umgebungsentitäten ergänzt: Außentemperatur, Außenhelligkeit, Windrichtung, Niederschlagsmenge heute und Luftfeuchtigkeit.
- Optionale Entitäten werden in der zentralen Backend-Zuverlässigkeitsbewertung anhand von Werteplausibilität und Aktualität berücksichtigt; fehlende oder ungeeignete Werte werden ausgelassen.
- Änderungen an den optionalen Entitäten lösen eine unmittelbare Neuberechnung der betroffenen Prognosesensoren aus.
- Konfiguration und Übersetzungen Deutsch/Englisch aktualisiert.
- Regressionstests für optionale, fehlende, ungültige und veraltete Umgebungswerte ergänzt.

## 0.0.2-beta-r149 – 2026-11-26

- Prognosesensoren: Laufzeitfehler `NameError: period_end_date is not defined` behoben. Die Zuverlässigkeits-Kontextprüfung verwendet jetzt die im Berechnungsablauf tatsächlich definierte Periodenendvariable `end_date`. Zuvor brach jede Prognoseaktualisierung nach erfolgreicher Forecast-Berechnung vor der Übergabe der Zuverlässigkeitsattribute ab.
- Qualitätssicherung: Regressionstest ergänzt, der die fehlerhafte Variablenreferenz verhindert.
- Qualitätssicherung: realer Forecast-Berechnungsaufruf und anschließende Ableitung der Modulgewichte sowie Zuverlässigkeitsaggregation ohne Messhistorie werden gemeinsam geprüft.
- Veraltete Revisionserwartungen in Regressionstests auf R149 aktualisiert.

## 0.0.2-beta-r148 – 2026-11-26

- Sensorinitialisierung: fehlenden Import `Store` aus `homeassistant.helpers.storage` ergänzt. Dadurch kann `async_added_to_hass` den persistenten Lernspeicher für Prognosesensoren anlegen und laden, statt mit `NameError` abzubrechen.
- Dashboard: Beschriftung „Anteiliger angefallener Grundpreis“ in „Anteiliger Grundpreis“ geändert; Berechnung und vollständige interne Preisgenauigkeit bleiben unverändert.
- Regressionstest ergänzt, der den `Store`-Import auf Modulebene und die Verwendung im Sensor-Lifecycle absichert.

## 0.0.2-beta-r147 – 2026-11-26

- Zuverlässigkeit: gemeinsame, getestete Ableitung der Modulgewichte aus den tatsächlichen Euro-Ergebnissen der Prognose. Modul A wird nach dem prognostizierten Energiewert gewichtet; Modul B nach dem prognostizierten finanziellen Gesamteinfluss einschließlich gebuchter und geplanter Kontobewegungen. Damit fällt Modul B nicht mehr allein deshalb aus der Aggregation, weil im Zeitraum noch keine Sonderbuchung oder Abschlagsbuchung existiert. Bei tatsächlich null Euro Einfluss werden weiterhin keine künstlichen Gewichte erzeugt.
- Sensor und Zuverlässigkeitsmodul verwenden dieselbe zentrale Gewichtungsfunktion. Verbrauch und Einspeisung bleiben durch getrennte Forecast-Kontexte isoliert.
- Regressionstests ergänzen reale Euro-Komponenten, Modulverfügbarkeit ohne Messhistorie und den Ausschluss künstlicher Gewichte bei null finanziellem Einfluss.

# Changelog

## 0.0.2-beta-r146 – 2026-11-26

- Abschlagsdialog: Vorgemerkter Hinweis zeigt nur noch die nächste tatsächliche Betragsänderung. Monatsweise Fortführung desselben Betrags erzeugt keinen wiederholten Hinweis; nach Wirksamwerden verschwindet der Hinweis automatisch, solange keine weitere abweichende Änderung folgt.
- Zuverlässigkeit: Bewertungsmodule erhalten die tatsächlich prognostizierten monetären Einflussgrößen einschließlich angefallener Grundpreise. Damit können verfügbare aktuelle Mess- und Finanzdaten auch ohne historische Vergleichsdaten eine nachvollziehbare Bewertung liefern. Historische Vergleiche bleiben optional und werden erst ab 24 gültigen Stundenvergleichen berücksichtigt.
- Zuverlässigkeitsstatus: Während der Initialisierung wird bei fehlendem Ergebnis innerhalb des 15-Minuten-Fensters „Zuverlässigkeit: wird ermittelt“ mit animiertem Indikator angezeigt; ein vorhandener Prozentwert wird unmittelbar verwendet. Es werden weiterhin keine Ersatz- oder Mindestwerte erzeugt.
- Dashboard-Beschriftung „Ø Aktuell im Monat“ in „Ø im Monat“ geändert.
- Release-Metadaten und Regressionstests auf R146 aktualisiert.

## 0.0.2 Beta – R145

- Monthly-advance selector now offers the next seven calendar months even when they cross into a subsequent billing period. Saving calculates the end of the billing period containing the selected effective month and applies the amount only through that period boundary.
- Reliability initialization now exposes a bounded pending state for the first 15 minutes when no evidence-based score is yet available, allowing the frontend to show the agreed animated “Zuverlässigkeit: wird ermittelt” indicator. A valid percentage remains immediately visible when available; no synthetic score is generated.
- Updated regression tests and release documentation.

## 0.0.2 Beta – R144
- Monatsabschlagsdialog: aktueller Monat bleibt gesperrt; auswählbar sind höchstens die nächsten sieben Monate und nur innerhalb des Abrechnungszeitraums.
- Serverseitige Validierung verhindert auch bei manipulierten oder veralteten Formulareingaben eine Änderung im aktuellen Monat oder außerhalb der angebotenen Monate.
- Dialoghinweise werden mit echten Zeilenumbrüchen dargestellt; aktuelle und vorgemerkte Abschläge bleiben getrennt und lesbar.
- Gesamtbeträge bei „Gesamt geleistete Zahlungen“ und „Gesamt erhaltene Zahlungen“ werden durch eine gemeinsame CSS-Klasse ausdrücklich fett dargestellt.
- Der native Home-Assistant-Optionsflow stellt den Absende-Button und das Schließen über das X bereit; frei benannte zusätzliche Aktionsbuttons „Abbrechen“ und „Fertigstellen“ sind in diesem nativen Formtyp nicht unterstützt. Das X verwirft ungespeicherte Eingaben, der Absende-Button schließt den Speichervorgang ab.

### Validierung
- 491 automatisierte Tests bestanden; Python-/JavaScript-Syntax, JSON, Übersetzungsparität und Archivprüfung bestanden. Home-Assistant-Laufzeittest ausstehend.


## 0.0.2 Beta – R143
- Entfernte doppelte Abschlagszeilen oberhalb der Bereiche „Bereits gezahlt“ und „Bereits erhalten“.
- Korrektur- und Sonderzahlungszeilen erscheinen vor der Gesamtsumme; der Gesamtbetrag wird rechts immer fett dargestellt.
- Die Kontostandsberechnung berücksichtigt die bis zum aktuellen Monat fälligen vertraglichen Monatsabschläge einschließlich monatlicher Betragsänderungen.
- Die separat ausgewiesenen, tatsächlich manuell gebuchten Abschläge bleiben als Nachweisinformation erhalten; sie werden nicht zusätzlich zu den automatischen Monatsabschlägen doppelt gezählt.
- Verbrauchs-Beispiel regression-getestet: 800,00 € Abschläge − 66,00 € Korrektur gegenüber 606,38 € Kosten ergeben 127,62 € Guthaben.
- Tests für Monatsgruppierung, Einzelmonatsformat, doppelte Anzeige, Reihenfolge, Fettdruck und Kontostand ergänzt; überholte Revisionserwartungen aktualisiert.

### Validierung
- 487 automatisierte Tests bestanden. Python-Kompilierung, JavaScript-Syntax, JSON-Validität, Übersetzungsparität und ZIP-Integrität geprüft. Home-Assistant-Laufzeittest bleibt ausstehend.

## 0.0.2 Beta – R142
- Zuverlässigkeit: künstlicher Startwert (einschließlich fester Basis 28 %) und zugehörige persistierte Initialisierung vollständig entfernt. Die Anzeige wird unmittelbar aus verwertbaren aktuellen Daten und abgeschlossenen Prognosevergleichen berechnet.
- Zuverlässigkeitsmodule A/B: keine Ersatzgewichte mehr. Module ohne nachweisbaren finanziellen Einfluss werden ausgelassen; verfügbare Modulgewichte stammen aus den jeweiligen Euro-Auswirkungen der Prognose.
- Modul A verwendet die Aktualität des tatsächlichen Zähler-Messwerts als Live-Evidenz; Zeit, Jahreszeit und Sonnenstand bleiben Prognoseeingänge, werden aber nicht pauschal als Zuverlässigkeitsbeweis mit 100 % bewertet.
- Modul B berücksichtigt nur vorhandene und valide Tarif-, Abrechnungszeitraum- und Steuergrundlagen. Fehlende optionale Buchungen oder Abschlagsplanungen erzeugen keinen Bonus und keine Zahlung.
- Historische Prognoseabweichungen fließen erst ab 24 gültigen Stundenvergleichen ein. Fehlt eine Bewertungsgrundlage vollständig, wird kein Prozentwert erfunden; die Karte zeigt dann „keine Bewertungsgrundlage“ statt eines endlosen Ladeindikators.
- Tarife werden in der Karte mit genau zwei Nachkommastellen dargestellt; interne Dezimalwerte und Berechnungen bleiben ungerundet.
- Zahlungsanzeige: doppelte Gesamtzahlungszeilen entfernt; Einspeisung verwendet „Gesamt erhaltene Zahlungen“.
- Veraltete Regressionserwartungen an künstliche Startwerte und sechsstellige Tarifdarstellung entfernt/angepasst; neue Tests für fehlende Modulgewichte und nicht verfügbare Bewertungsgrundlagen ergänzt.

### Validierung
- 483 automatisierte Tests bestanden. Python-/JavaScript-Syntax, JSON-Validität, Übersetzungsparität und ZIP-Integrität geprüft. Home-Assistant-Laufzeittest bleibt ausstehend.

## 0.0.2 Beta – R141
- Zahlungsübersicht: Abschnitt „Vorgemerkte Abschläge“ entfernt.
- Jeder bereits begonnene/abgelaufene Monat des aktuellen Abrechnungszeitraums wird gemäß Projektvorgabe als gezahlter Monatsabschlag berücksichtigt; zukünftige Monate bleiben ausgeschlossen.
- Abschläge werden nach zusammenhängenden Monaten mit identischem Betrag gruppiert. Einzelmonate erscheinen als „April (250,00 €)“, mehrere Monate als „Mai – September (5 × 200,00 €)“.
- Monatsgruppen und Abschlagssummen werden backendseitig aus der effektiven Monatshistorie geliefert; explizite Buchungen erzeugen keine Doppelzählung und unterbrechen keine identische Betragsgruppe.
- Gesamt geleistete Zahlungen wird unabhängig davon angezeigt, ob Korrekturen vorhanden sind; Offener Betrag/Guthaben bleibt darunter bestehen.
- Historische Prognoseabweichungen werden erst ab 24 gültigen Stundenvergleichen berücksichtigt.
- Regressionstests an die neue Abschlags- und Zuverlässigkeitslogik angepasst und erweitert.

## 0.0.2 Beta – R140
- Monatsabschläge: Auswahl zukünftiger Wirksamkeitsmonate mit ausgeschriebenem Monatsnamen und Jahreszahl (z. B. „Dezember 2026“).
- Abschlagsdialog: aktueller Betrag und bereits vorgemerkte zukünftige Änderung werden getrennt angezeigt; erfolgreiche Speicherung wird bestätigt.
- Abschlagshistorie: monatliche Beträge werden backendseitig innerhalb des aktiven Abrechnungszeitraums nach Betrag gruppiert; ein neuer Abrechnungszeitraum beginnt mit einer neuen Gruppierung.
- Zahlungsübersicht: fällige/vorgemerkte Abschläge werden separat von nachgewiesenen Zahlungen dargestellt. Automatische Sollbeträge gelten nicht als Zahlungseingang.
- Regressionstests für Jahreswechsel, Wirksamkeitswechsel, Abrechnungsperiodenende und explizite Zahlungsbuchungen ergänzt.

## [0.0.2-beta-r139] - 2026-11-26

### Geändert
- Zuverlässigkeitsberechnung in einen erweiterbaren Backend-Modulaggregator überführt. Module A (Prognosequalität) und B (finanzielle Prognosequalität) liefern getrennte Beiträge; nach außen bleibt eine einzelne Prozentanzeige.
- Bewertungsmodule werden über eine offene Registrierung eingebunden; es gibt keine feste Begrenzung auf A/B/C/D. Weitere Module können ohne Änderung des Aggregators ergänzt werden.
- Fehlende Messhistorie wird nicht als negativer Faktor gewertet. Historische Prognosequalität fließt erst ein, wenn mindestens fünf abgeschlossene Stundenvergleiche vorliegen.
- Künstliche Zuverlässigkeitsuntergrenzen und zufällige Startwerte entfernt. Ergebnisse unter 10 % sind zulässig; identische Eingaben liefern identische Ergebnisse.
- Regressionstests für Gewichtung, fehlende Historie, offene Modulerweiterung, fehlende Daten und Werte unter 10 % ergänzt; bestehende Tests angepasst.

### Validierung
- 479 automatisierte Tests bestanden; Python-Kompilierung, JavaScript-Syntax, JSON-Validierung und DE/EN-Schlüsselparität erfolgreich. Home-Assistant-Laufzeittest bleibt ausstehend; Details in `docs/TEST_REPORT_R139.md`.

## [0.0.2-beta-r137] - 2026-11-26

### Geändert
- Aktuelle Watt-Anzeige in den Zählerkarten farblich an das Verhältnis von Einspeisung zu Verbrauch gekoppelt: grün bei höherer Einspeisung, rot bei niedrigerer Einspeisung und grau bei gleichen Werten.
- Ohne positive aktuelle Einspeisung bleibt die bisherige graue Anzeige erhalten.
- Ausschließlich der Text „123 Watt“ wird eingefärbt; es werden keine Icons oder zusätzlichen Texte ergänzt. Messwerte und Berechnungen bleiben unverändert.
- Regressionstests für alle Farbzustände und den unveränderten Fall ohne Einspeisung ergänzt.

### Validierung
- 474 automatisierte Tests bestanden; Python-Kompilierung, JavaScript-Syntax, JSON-Validierung und DE/EN-Übersetzungsstruktur geprüft. Home-Assistant-Laufzeitdarstellung muss weiterhin in der Installation geprüft werden.

## [0.0.2-beta-r136] - 2026-11-26

### Änderungsübersicht
- Neuer Menüpunkt „Monatsabschlag ändern“ zwischen „Buchungen verwalten“ und „Monatsabschläge bearbeiten“ ergänzt.
- Eigenständigen Ablauf zum Auswählen von Stromzähler und Abrechnungsbereich sowie zum Festlegen eines zukünftigen Wirksamkeitsmonats und neuen Betrags ergänzt.
- Neue Abschlagshöhe wird ab dem gewählten Monat bis zum Ende des laufenden Abrechnungszeitraums gespeichert; frühere Monate bleiben unberührt.
- Anzeige des aktuell gültigen Abschlags einschließlich Gültigkeitsdatum bei bereits erfolgter Änderung ergänzt.
- Deutsche und englische Übersetzungen sowie Regressionstests erweitert.

### Validierung
- 470 automatisierte Tests bestanden.
- Python-Kompilierung und JSON-Validierung erfolgreich.
- JavaScript-Syntaxprüfung erfolgreich.
- Ein vollständiger Home-Assistant-Laufzeit- und Browserdialogtest ist nicht Bestandteil der automatisierten Prüfung.

## [0.0.2-beta-r134] - 2026-11-26

- Fixed the feed-in monthly-advance editor so its displayed defaults and the legacy repair migration use the same contract-value resolution.
- Restored the legacy `monthly_advance` fallback only for feed-in-only contracts; consumption advances are never reused as feed-in payouts for combined contracts.
- Added regression tests for canonical values, legacy feed-in-only values, direction separation, and invalid/negative legacy data.
- Slowed the initial reliability spinner to one rotation every three seconds.
- Clarified the unavailable monthly-advance text with the agreed wording “derzeit noch nicht”.

## [0.0.2-beta-r133] - 2026-11-26

### Fixed
- Kept the reliability row visible on enabled forecast cards even when the forecast sensors do not yet expose the reliability attributes. The pending state now includes the rotating indicator.
- Kept the monthly-advance section visible whenever the corresponding forecast is enabled. If no valid numeric recommendation is available, the card displays a localized explanation instead of silently omitting the section.
- Added focused regression tests for missing reliability attributes and unavailable monthly-advance sensor values.

### Validation boundary
- Automated tests and static checks are recorded in `docs/TEST_REPORT_R133.md`.
- A live Home Assistant startup and browser rendering test still require validation in the user's installation.

## [0.0.2-beta-r132] - 2026-11-26

### Changed
- Replaced the randomized six-hour reliability startup with a deterministic, meter- and direction-specific assessment. The card may show an initial pending state for at most 15 minutes; a five-minute refresh ensures the display transitions within that window.
- After the initial window, reliability is always numeric: completed hourly forecast comparisons are used when at least five are available; otherwise a bounded score is calculated from available historical data quality, coverage, history length, and sample count. This fallback is explicitly labelled internally as data-foundation quality, not measured forecast accuracy.
- Added a rotating loading indicator beside the localized “Wird ermittelt” / “being determined” text, respecting reduced-motion preferences.
- Feed-in power is displayed as an absolute value in the card only; source states, database values, billing, and forecasts are unchanged.
- Corrected the feed-in payment total label to “Gesamt erhaltene Zahlungen:” (English: “Total payments received:”). Consumption retains “Gesamt geleistete Zahlungen:”.
- Kept the forecast end-date heading on one line where the available card width permits, using responsive text sizing.

### Validation boundary
- Automated checks are run for this revision and recorded in `docs/TEST_REPORT_R132.md`.
- A live Home Assistant startup, Recorder integration test, and browser layout test still require validation in the user's installation.

## [0.0.2-beta-r131] - 2026-11-26

### Fixed
- Corrected the remaining feed-in monthly-advance editor defect: R128/R129 could persist the contract-default payout as an explicit zero monthly override, and the R130 reader then treated that legacy row as an intentional manual zero.
- Added a one-time, per-meter/per-contract SQLite data migration. When the latest active feed-in monthly override is zero, it is replaced with the selected contract's gross monthly payout amount. The former row is marked superseded and retained in the audit history; the replacement records the migration reason and superseded row ID.
- The migration marker is persisted even when no legacy zero is found. Subsequent openings therefore cannot overwrite a future, intentionally entered zero amount.
- The editor derives the migration default from the canonical net `feed_in_monthly_advance` contract value and converts it to the gross payout amount using the contract VAT rate. A legacy feed-in-only contract falls back to its old `monthly_advance` field.
- The migration is scoped to the selected meter and contract and runs before the monthly form is displayed. Consumption advances and unrelated meters/contracts are untouched.
- Advanced the release and frontend cache-busting identifiers to `0.0.2-beta-r131`.

### Tests
- Added regression tests for legacy zero repair, audit preservation, gross amount restoration, migration idempotence, preservation of future intentional zero overrides, meter/contract isolation, and editor integration.

### Validation boundary
- Automated tests and static checks do not replace a live Home Assistant startup and verification against the user's actual database. This limitation is stated in the release test report.

## [0.0.2-beta-r130] - 2026-11-26

### Fixed
- Fixed the root cause of missing dashboard cards: the static HTTP route was registered from both `async_setup` and `async_setup_entry`, and the duplicate-registration exception caused the second call to return before registering the Lovelace resource.
- Made static-route registration idempotent and separated it from Lovelace resource registration. An already-registered route is now treated as healthy rather than as a fatal error.
- Added a single delayed retry when Lovelace or its storage resource collection is not ready during integration setup. The retry is cancelled after success and repeated setup calls cannot create parallel retry timers.
- Existing Lovelace resources are updated in place with the current versioned JS URL and `module` resource type; registration does not create duplicates.
- Preserved YAML resource mode as a manually managed configuration.
- Advanced the frontend cache-busting version to `0.0.2-beta-r130`.

### Tests
- Added behavior-level regression tests for early setup, subsequent setup, delayed retry, resource version update without duplication, YAML mode, and presence of both custom card definitions.
- Full suite and package validation results are recorded in `docs/TEST_REPORT_R130.md`.

### Validation boundary
- Automated tests and static checks do not replace a live Home Assistant startup and browser test. The final report explicitly records this limitation.

## [0.0.2-beta-r129] - 2026-11-25

### Fixed and improved
- Exposed the exact gross feed-in tariff precision in the card (up to six decimals) so the displayed tariff explains the cent-exact remuneration calculation; for example, 28.74 ct/kWh net at 19% VAT is 34.2006 ct/kWh gross and correctly produces 1,840.70 € for 5,382.059 kWh.
- Aligned forecast energy costs with the same projected kWh used by the historical, seasonal, solar, sunrise/sunset, and per-meter compass-direction model. The previous code calculated this energy projection but then used a separate linear cost extrapolation, silently discarding those model inputs from the expected account balance.
- Extended forecasts to the exact current instant and through the full final billing day, including the remaining fraction of today without double-counting measured energy. Explicit billing-period end dates are now used consistently.
- Aligned forecast base-price accrual with the live balance using continuous local-time proration with leap-year-aware annual denominators, and froze the charge at the exclusive billing-period boundary.
- Included additional payments, credits, and signed corrections in forecast account balances. Corrections are no longer incorrectly treated as recurring extra charges. One-off extra charges are included once and are not extrapolated as recurring daily costs.
- Corrected future feed-in advance scheduling to include VAT and use the actual configured amount for each future month.
- Fixed the feed-in monthly-advance editor: it now reads the canonical `feed_in_monthly_advance` value from the selected contract, converts the stored net value back to the gross payout amount using the configured VAT, and uses this as the default for months without an explicit monthly override. This now matches the consumption editor.
- Kept explicit per-month overrides (including a deliberately entered `0.00 €`) authoritative. New manual values are marked as such; legacy zero records created by the R128 defaulting bug fall back to the configured contract amount until explicitly edited. Superseded monthly records are ignored.
- Limited the randomized reliability startup value to six hours. Thereafter reliability uses measured hourly comparisons (from five completed hours) or qualifying historical evidence; if neither exists, the card displays that reliability is still being determined.
- Made an explicitly empty feed-in orientation selection use the neutral four-direction historical solar model instead of silently defaulting to south.

### Tests
- Added fixed regression cases for exact feed-in tariff arithmetic, exact current-time horizon, final billing-day inclusion, partial-day seasonal projection, account corrections/payments/credits, one-off charges, six-hour reliability expiry, neutral orientation, and direction-sensitive monetary forecasts.
- Updated earlier tests whose expected values assumed whole-month base-price accrual, two-decimal tariff display, or one-off charges being extrapolated.
- Full automated regression suite: **440 passed**.

### Validation and limitation
- Python compilation and JavaScript syntax checks pass; all automated tests pass.
- Full Home Assistant runtime/Recorder/browser verification has not been performed in this environment. The changes remain in the working review copy and have not been packaged into a ZIP.

## [0.0.2-beta-r128] - 2026-11-25

### Changed
- Moved feed-in compass direction assignment into the individual meter editor; removed the former global forecast-direction selection and replaced the mandatory single-direction step with an optional per-meter multi-select step.
- Each feed-in meter now supports any combination of north, east, south, and west, or an explicitly empty selection. New feed-in meters default to south.
- Migrated legacy single-direction and multi-direction values into the new per-meter list without discarding existing valid selections.
- Kept feed-in forecasting available when no direction is selected; the initial solar prior then uses a neutral four-direction average instead of silently assuming south.
- Replaced recommendation/action wording with the neutral label “Voraussichtlicher monatlicher Abschlag” and neutral explanatory text. Added a thin divider and spacing before the unavailable-reason text.
- Restored the thin divider below the current meter reading and aligned the billing-period progress text to the current-power line typography.

### Tests
- Added R128 tests for south as the new-meter default, empty and multi-direction persistence semantics, legacy-value normalization, neutral no-direction solar prior, multi-direction combination, and forecast availability without a direction.
- Extended forecast-card regression tests for neutral wording and the divider before explanatory text.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, translation parity, automated tests, and ZIP integrity are checked for this package.
- The native Home Assistant config-flow selector supports multi-selection but does not expose a supported two-column layout option; the two-column checkbox presentation remains an open UI limitation.
- A live Home Assistant startup and browser-rendering test is not available in the build environment.

## [0.0.2-beta-r127] - 2026-11-25

### Changed
- Moved forecast reliability directly below the forecast heading; the forecast section therefore starts higher and follows the approved order: season, heading, reliability, expected billing balance, then recommendation or explanation.
- Added German and English explanations when no monthly advance recommendation is shown: final payment period, no remaining payment gap, insufficient measured reliability, or a generic unavailable basis.
- Exposed the insufficient-reliability reason from the forecast sensor so the card does not silently omit the recommendation area.
- Corrected the diagnostic flag for final-payment-period protection so it reflects the actual `months_remaining < 2` rule.

### Tests
- Added R127 regression tests for exact forecast-card ordering, localized reason-specific recommendation explanations, sensor reason propagation, and the final-period diagnostic.
- Updated the existing final-period protection test to expect the active protection flag.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, translation parity, automated tests, and ZIP integrity are checked for this package.
- The two-column compass-direction checkbox layout remains outstanding; the native config-flow selector has no supported column-layout option.
- A live Home Assistant startup, Recorder-load, and browser-rendering test is not available in the build environment.

## [0.0.2-beta-r126] - 2026-11-25

### Changed
- Moved forecast reliability directly below the season label and immediately above the forecast heading, matching the latest approved card order.
- Increased the current consumption/feed-in line typography slightly and widened the label/value gap while retaining a right-aligned Watt value.
- Added the missing thin divider below the combined billing-period progress/current-power row and above the work-price/feed-in tariff row.
- Retained the no-divider treatment below the tariff row because the thicker finance-section divider follows it.

### Tests
- Updated forecast-card ordering and current-power typography regression assertions.
- Added a dedicated R126 regression test for the period-meta divider, current-power layout, tariff divider suppression, and forecast ordering.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, German/English translation parity, the complete automated test suite, and ZIP integrity are checked for this package.
- The two-column compass-direction checkbox layout remains outstanding; the native Home Assistant config-flow selector does not provide a supported column-layout option.
- A live Home Assistant startup, Recorder-load, and browser-rendering test is not available in the build environment. Final visual verification remains necessary in the target installation.

# Changelog

## 0.0.2 Beta – R145

- Monthly-advance selector now offers the next seven calendar months even when they cross into a subsequent billing period. Saving calculates the end of the billing period containing the selected effective month and applies the amount only through that period boundary.
- Reliability initialization now exposes a bounded pending state for the first 15 minutes when no evidence-based score is yet available, allowing the frontend to show the agreed animated “Zuverlässigkeit: wird ermittelt” indicator. A valid percentage remains immediately visible when available; no synthetic score is generated.
- Updated regression tests and release documentation.

## [0.0.2-beta-r125] - 2026-11-25

### Fixed and improved
- Addressed Home Assistant slow entity-update warnings for the annual-balance and monthly-advance forecast sensors.
- Replaced synchronous forecast calculation in the `native_value` property with an O(1) cached-value read.
- Moved the CPU-intensive forecast projection to Home Assistant's executor using an immutable input snapshot.
- Serialized overlapping refreshes and refreshed the cached value after source-meter changes, hourly learning updates, history refreshes, and hourly season/solar refreshes.
- Kept forecast attributes and the cached state value updated together; unavailable source entities and invalid billing bases now explicitly clear the cached state and expose a diagnostic status.
- Preserved the R124 forecast model, recommendation rules, card layout, data structures, and entity unique IDs.
- Updated README, architecture notes, requirements, and the R125 test report.

### Tests
- Added regression tests proving `native_value` only returns the cached value.
- Added checks that forecast calculation is delegated to the executor and that source/season callbacks schedule an asynchronous refresh.
- Added checks for serialized refreshes and initial cache state.
- Full regression suite: **413 passed**.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, translation parity, and ZIP integrity passed.
- A live Home Assistant startup/Recorder timing test was not available in the build environment. The original warning should therefore be rechecked after installing R125; the slow synchronous calculation path that caused it has been removed from entity state updates.

This file records all relevant changes included in released VerbrauchsMonitor versions.

The public change history starts with the first released version.

## [0.0.2-beta-r124] - 2026-11-25

### Fixed and improved
- Extended the local solar model to use solar elevation, azimuth, daylight duration, and calculated local sunrise/sunset for both consumption and feed-in forecasts.
- Added a bounded astronomical daylight-demand adjustment to the consumption profile; low-sun/short-day conditions can influence the projected future demand without replacing measured household history.
- Applied a bounded solar correction to history-based future projections for both directions; selected feed-in compass directions now also refine the historical seasonal projection, not only the first-install profile.
- Kept historical monthly meter rates as the dominant forecast evidence and applied solar geometry only to the future portion of the billing period.
- Suppressed monthly advance recommendations when fewer than two future payment dates remain or when no positive payment gap remains after booked and scheduled payments.
- Removed the artificial 70% recommendation floor that could create an economically unjustified amount despite an existing credit or scheduled payments.
- Moved current consumption/feed-in power to the right side of the compact elapsed-period subline, with the same small typography and a tighter label/value gap; removed the thin divider below that line.
- Moved the season label above the forecast heading, retained the expected balance and reliability below the heading, and removed the redundant divider below the expected balance.
- Updated the card, integration constants, README, architecture notes, requirements register, and test report to Beta R124.

### Tests
- Added fixed reference tests for winter/summer solar demand profiles, sunrise/sunset in the configured timezone, directional feed-in effects, history-based solar adjustments for both directions, final-payment-month recommendation suppression, and scheduled-payment deduction.
- Updated previous recommendation tests to assert that one remaining payment date never produces a new monthly recommendation and that scheduled future payments are deducted before dividing the remaining gap.
- Retained fixed numeric reference cases for meter readings, tariffs, VAT, base prices, payment allocation, and cent-exact balances.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, German/English translation parity, unit/regression tests, and ZIP integrity are checked for this package.
- The requested two-column compass-direction checkbox layout remains outstanding. The native Home Assistant config-flow selector supports multiple selection but exposes no supported column-layout parameter; a dedicated custom config-flow frontend is still required.
- A live Home Assistant startup/Recorder/browser test is not available in the build environment. Sunrise/sunset values, Recorder learning, entity availability, registry migration, and visual rendering still require validation in the target HA instance.

## [0.0.2-beta-r123] - 2026-11-25

### Fixed
- Added the missing hourly-learning refresh callback and shared-store reload method to the forecast sensor class itself. This prevents monthly recommendation entities from failing initialization because a callback existed only on the balance sensor class.
- Forecast sensor startup now resolves the Home Assistant instance from the entity or owning entity platform before registering event/time listeners and before entity-registry migration.
- The forecast card now orders its content as requested: forecast heading, expected billing balance, reliability, season, and monthly advance recommendation.
- Moved the current consumption/feed-in power line below the billing-period amount and its progress subline. It now uses the same compact 9px secondary-text treatment as the progress line, with a reduced label/value gap.
- Removed the redundant thin divider below the tariff row where the thicker finance-section divider follows.

### Tests
- Added AST-based regression tests proving the monthly forecast entity owns the required hourly-learning callbacks and that startup does not pass an unresolved `None` Home Assistant reference to the state-change helper.
- Added layout regression tests for forecast ordering, current-power row placement and typography, and removal of the redundant tariff divider.
- Retained fixed-value reference tests for known meter readings, tariffs, VAT, base prices, payments, and money rounding.

### Validation and limitation
- Python compilation, JavaScript syntax, JSON parsing, translation checks, unit/regression tests, and ZIP integrity are run for this package.
- The two-column compass-direction checkbox layout remains outstanding: the Home Assistant native config-flow list selector has no supported column-layout setting. Multiple selection and translated labels remain intact; a custom config-flow frontend is required to implement the two-column visual layout correctly.
- A live Home Assistant runtime/browser test is not available in the build environment. Entity lifecycle, Recorder callbacks, and visual rendering still require validation in the target HA instance.

## [0.0.2-beta-r122] - 2026-11-25

### Fixed
- Forecast reliability initialization is now shared by the annual-balance and monthly-advance sensors for each logical meter and direction. A stable per-meter/direction seed prevents concurrent entity setup from generating conflicting initial values.
- The forecast card now displays an available initial reliability value even when it is below the former 37.6% display threshold, and clearly labels it as provisional.
- A provisional monthly advance recommendation is now displayed alongside the initial model value; it is explicitly labelled provisional until hourly measured reliability becomes available.
- The monthly-advance forecast entity reloads the shared hourly learning store so measured reliability and recommendation availability stay synchronized with the annual forecast entity.
- Monetary balance and forecast entities now suggest exactly two display decimals.
- Existing entity registry IDs are migrated to the canonical `sensor.verbrauchsmonitor_<meter>_<direction>_<role>` object ID where the target is not occupied by another entity. The migration retains the existing unique ID and refuses collisions.
- Database information now reads contract and meter counts from ConfigEntry options and reports the number of configured meter-reading source entities.

### Tests
- Added regression tests for initial reliability visibility, provisional recommendation rendering, shared hourly-learning refresh, two-decimal monetary precision, safe entity-ID migration, and exact configured counts (2 contracts, 2 meters, 3 reading entities).
- Retained the fixed-value billing reference tests for deterministic readings, tariffs, VAT, base price, and payments.

### Validation
- Python compilation, JavaScript syntax, JSON parsing, translation structure parity, unit/regression tests, and ZIP integrity are checked for this release. A live Home Assistant runtime/browser test cannot be performed in the build environment.

## [0.0.2-beta-r120] - 2026-11-25

### Fixed
- Removed the stale hourly reliability timer registration that referenced a deleted callback and prevented all four forecast entities from being added to Home Assistant.
- Defined consumption and feed-in power entities in the billing-card render scope, preventing JavaScript `ReferenceError` exceptions that broke card rendering.

### Tests
- Added regression checks ensuring forecast setup never registers missing callbacks.
- Added regression checks ensuring billing-card power variables are declared in the same render scope before use.

## [0.0.2-beta-r119] - 2026-11-25

### Added
- Deterministic reference-case regression test with fixed meter readings, tariff, VAT, base price, and payment values.
- Exact-timestamp annual base-price accrual helper and regression tests.
- Direct database-administration navigation separated from individual reset scopes.

### Changed
- About dialog now receives version, release stage, and revision from centralized release constants.
- Monthly elapsed-period display now uses the current timestamp, two decimal places for fractional values, and localized decimal formatting.
- Current consumption/feed-in power is displayed directly below the corresponding meter reading when configured.
- Compass-direction fields no longer expose UUID-based field names; legacy direction values are retained as migration fallbacks.

### Fixed
- Removed the database checkbox from the individual reset form; database administration is a direct navigation destination.
- Accrued base price is calculated continuously from billing-period start to the current timestamp rather than rounding up to whole months.

### Validation
- Automated tests and static checks are run for this package. A live Home Assistant runtime test is not available in this build environment.

## [0.0.2-beta-r121] - 2026-11-25

### Fixed
- Fixed a billing-card JavaScript scope error: the billing card now uses its locally defined `valid()` helper when deciding whether to render the optional current-power row. This prevents `ReferenceError: hasValue is not defined` and restores the affected billing cards.

### Tests
- Added regression coverage for the billing-card helper scope and for hiding the optional power row when its entity is missing or unavailable.

### Validation
- Python unit tests, Python compilation, JavaScript syntax, JSON validation, and archive integrity are checked for this release. A live Home Assistant browser/runtime test remains necessary.

## [0.0.2-beta-r135] - 2026-11-26

### Changed
- Billing cards show the total received/paid payment row only when at least one correction exists; the row remains after the correction line and before the final balance.
- Forecast reliability is no longer held back by an artificial 15-minute delay. A deterministic evidence-based value is shown as soon as the available inputs permit calculation; 15 minutes remains the maximum initial wait, not a minimum.
- Updated the unavailable-recommendation message to the approved wording: “Ein voraussichtlicher monatlicher Abschlag wird gerade berechnet.”

### Tests
- Added regression coverage for conditional payment totals, ordering, approved recommendation wording, and immediate/15-minute reliability availability.

## [0.0.2-beta-r152] - 2026-11-26

### Changed
- Monthly advance recommendations are no longer suppressed by an unavailable reliability percentage. The recommendation is shown whenever its own forecast calculation is valid; reliability remains an independent, evidence-based value.
- The reliability percentage is not given an artificial minimum. No extra Home Assistant entities are created.

### Added
- Hourly learning data now has a second persistent Home Assistant Store copy per config entry and direction. On startup or refresh, an empty/missing primary store is restored from the backup when it contains valid learning records.
- Persisted learning state is structurally validated while retaining valid forecast/evaluation rows and unknown metadata, protecting compatible future extensions.

### Tests
- Added regression tests for recommendation visibility independent of reliability, learning-state restoration/validation, stable per-entry/per-direction storage keys, and primary/backup persistence.

### Validation
- Automated tests: 515 passed. Python/JavaScript/JSON and archive checks are performed for the release package. A live Home Assistant runtime test is not available in this build environment.

## [Unreleased]

### Added

- Local SQLite persistence with the primary database at `/config/verbrauchsmonitor.db` and a consistent single backup database at `/config/verbrauchsmonitor-backup.db`.
- One-time, lossless migration of the previous JSON data set during the first SQLite startup.

### Changed

- Work-price and feed-in tariff displays are limited to two decimal places; internal tariff precision and calculations remain unchanged.
- Persistent domain data is stored in SQLite transactions instead of the previous JSON store; JSON remains the import/export format.

### Fixed



## [0.0.2-beta-r160] - 2026-11-26

### Fixed
- Daily energy entities now use device-view-safe names (`Tagesverbrauch (heute)` and `Tages-Einspeisung (heute)`) so Home Assistant does not reduce their displayed names to only `(heute)` by stripping the matching device-name prefix. Known generated legacy registry names are migrated; deliberate custom names remain untouched.
- Daily sensors now fall back to the current real cumulative meter reading as a persisted partial-day baseline when Recorder history and long-term statistics cannot reconstruct midnight. The resulting value starts at 0 at integration initialization and increases with subsequent meter readings; the `partial_day` attribute explicitly discloses that earlier same-day energy could not be recovered.
- The partial-day flag is persisted and restored across Home Assistant restarts. Full-day baselines recovered from Recorder/statistics and new midnight baselines are marked as complete-day baselines.

### Tests
- Added behavioral tests for generated display names, legacy-name detection versus custom names, partial-day baseline initialization, increasing cumulative deltas, restart restoration semantics, and `total_increasing`/midnight behavior.
- Automated test suite: 547 passed.

### Validation limits
- The Home Assistant package/runtime is not installed in the build environment. Actual entity-registry update behavior, Recorder integration, device-page rendering, midnight event handling, and long-term statistics must still be confirmed in the user's Home Assistant instance.
