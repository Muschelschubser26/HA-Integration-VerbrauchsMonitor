# Verbindliche Anforderungsliste – VerbrauchsMonitor

Alle Anforderungen bleiben Projektumfang. Status `offen` bedeutet: noch nicht implementiert
und noch nicht als erfüllt getestet.

| ID | Anforderung | Status |
|---|---|---|
| VM-001 | Beliebig viele logische Zähler; Verbrauch/Einspeisung getrennt aktivierbar; stabile UUID; eindeutige fachliche Kennung | teilweise: mehrere logische Zähler und optionale Zählernummer; vollständige physische Zählerwechselhistorie offen |
| VM-002 | Individuelle Tarife, Netto/Brutto, MwSt., Grundpreise, Gültigkeitszeiträume | teilweise: Netto-Arbeitspreise Bezug/Einspeisung, daraus berechnete Bruttopreise, MwSt., Grundpreis und Intervall konfigurierbar; Preisgültigkeits-Historie offen |
| VM-003 | Beliebig viele physische Zählerwechsel; historische Abschnitte; Abrechnung läuft weiter | offen |
| VM-004 | Hochrechnung mit Verbrauch, Einspeisung, Kosten, Grundpreis, MwSt., Zahlungen und Wechseln | teilweise: Prognosen für Verbrauch/Einspeisung, Periodenkosten, Grundpreis und Zahlungstermine vorhanden; vollständige Wechselhistorie und Abrechnungssnapshots offen |
| VM-005 | Individuelle Abschläge, Soll/Ist-Zahlungen und Gültigkeitshistorie | teilweise: vertragliche Monatsabschläge, Monatswerte und Buchungshistorie vorhanden; weitergehende Gültigkeitshistorie offen |
| VM-006 | Beliebig viele Sonderzahlungen, Gutschriften und Korrekturen | umgesetzt: getrennte, zugeordnete Buchungsarten mit dauerhafter Speicherung |
| VM-007 | Zentrale Konfiguration unter Einstellungen → VerbrauchsMonitor/Zählerdaten | teilweise: zentrale Hub-Verwaltung über Config Flow und Options Flow; einzelne Verwaltungsabläufe bleiben mehrstufig |
| VM-008 | Individuelle Abrechnungszeiträume und optionale Enddaten | offen |
| VM-009 | Optionale DB; Abrechnung unabhängig von DB; Status und Wiederherstellung | teilweise: lokaler JSON-Datenspeicher mit Status, Optimierung, Import/Export und Reset; vollständige DB-unabhängige Abrechnung und Wiederherstellung offen |
| VM-010 | Deutsch/Englisch, getrennte Backend-/Frontend-Übersetzungen | technisch umgesetzt: deutsche und englische Übersetzungsschlüssel sind synchron; vollständige Sichtprüfung in einer laufenden HA-Oberfläche bleibt Zielsystemtest |
| VM-011 | Geplante Zählerwechsel mit Erinnerungen und getrennter Ist-Dokumentation | offen |
| VM-012 | Erinnerungen und Vorbereitung des nächsten Abrechnungszeitraums | offen |
| VM-013 | Unveränderlicher Snapshot 30 Minuten vor Abrechnungsende | offen |
| VM-014 | Über-Informationen mit Version, Entwickler und Supportkontakt | offen |
| VM-015 | Anzeigename und Zählernummer; Korrektur und physischer Wechsel getrennt behandeln | offen |
| VM-016 | Plausibilisierte automatische Wechselerkennung mit Nutzerbestätigung | offen |
| VM-017 | Regelmäßige Sicherungen 00/06/12/18 Uhr und 23:30 Uhr | offen |
| VM-018 | Neustart-/Shutdown-Verhalten ohne Nachholung verpasster Sicherungen | offen |
| VM-019 | Integrationsinterne, dauerhafte und DB-unabhängige Datenhaltung | offen |
| VM-020 | DB-Ausfall darf Abrechnung und Hochrechnung nicht beeinträchtigen | offen |
| VM-021 | DB-Historie, Prognosehistorie, Wochenaggregate und Aufbewahrung | offen |
| VM-022 | Live-Zählerstände sofort aktualisieren und dauerhaft sichern | offen |
| VM-023 | Direkte Zuordnung vorhandener HA-Sensoren; maximal je eine Entität pro Richtung/Messart | teilweise: Zählerstand und Momentanleistung je Richtung sowie optionale Außenhelligkeit zuordenbar |
| VM-024 | Einzelabrechnung je Zähler und Gesamtübersicht über alle Stromzähler | offen |
| VM-025 | Fehlende/ungültige Messwerte je Entität überwachen: 24h ohne Update, 1h unknown/unavailable | offen |
| VM-026 | Livewerte unverzögert; Abrechnungswerte plausibilisiert; Median-/Ausreißerlogik fachlich absichern | offen |
| VM-027 | Optionale Momentanleistung Verbrauch und Einspeisung in W | teilweise: Quell-Entitäten konfigurierbar und live gespiegelt; Plausibilisierung offen |
| VM-028 | Gesamt-Live-Saldo: Verbrauchsleistung minus Einspeiseleistung | offen |
| VM-029 | Hauptkarte mit Gesamtwerten und kompakten Einzelzählern | teilweise: responsive Karte je logischem Zähler mit Live- und Tarifdaten; automatische Ressourcenregistrierung im Lovelace-Storage-Modus; Aggregation und Tages-/Finanzwerte offen |
| VM-030 | Zählerdetail als modales Fenster; Abrechnung innerhalb desselben Dialogs | offen; separate Abrechnungskarte R033 vorhanden |
| VM-031 | Aktueller Saldo und Prognose getrennt darstellen | umgesetzt: aktueller Kontostand und erwarteter Prognosewert werden getrennt ausgegeben |
| VM-032 | Prognoseverfahren je Zähler und Messrichtung konfigurierbar | teilweise: Prognosen sind je Quellzähler und Messrichtung aktivierbar und zuordenbar; freie Wahl verschiedener Prognosealgorithmen ist nicht vorgesehen |
| VM-033 | Lineare und saisonale Prognose; automatische lineare Übergangsmethode bei Datenmangel | teilweise: R080 nutzt Recorder-Monatsprofile ab 12 Monaten und Zwei-Zyklen-Prüfung ab 24 Monaten; Fallback bei Datenmangel |
| VM-034 | Historische Wochen-/Saisonwerte langfristig nutzen; jüngere Datengewichtung noch festzulegen | teilweise: Recorder-Langzeitstatistiken bevorzugt, Detailhistorie als Fallback; monatliche und saisonale Tagesraten |
| VM-035 | Prognosequalität und Datenbasis in der Karte darstellen | teilweise: Zuverlässigkeitsindex und Historien-/Qualitätsattribute vorhanden; weitergehende Datenbasisdarstellung offen |
| VM-036 | Prognosebewertung wöchentlich, quartalsweise und zum Abrechnungsabschluss | offen |
| VM-037 | Einzelzuverlässigkeit je Zähler/Messrichtung und gleichberechtigte Gesamtzuverlässigkeit | teilweise: Einzelzuverlässigkeit je Zähler/Richtung; aggregierte Gesamtzuverlässigkeit offen |
| VM-038 | Bewertungslogik mit simulierten Daten prüfen und versionieren | offen |
| VM-039 | Prognoseverfahren intern vergleichen; keine automatische Umstellung ohne geprüfte Regeln | offen |
| VM-040 | Vollständige Lovelace-Karte, Dialoge, Editor, responsive Darstellung und Übersetzungen | teilweise: Live-Karte plus separate responsive Abrechnungskarte R033; Dialoge, historische Wechselverwaltung und vollständige Kartenkonfiguration offen |
| VM-041 | Supportdiagnose mit Vorschau, Redaktion und ausdrücklicher Zustimmung | offen |
| VM-042 | SemVer, Updatehinweise, Dokumentation, Logo, Tests und saubere Deinstallation | offen |

## Grundsatz
Keine Anforderung wird aus Umfangs- oder Implementierungsgründen stillschweigend entfernt,
vereinfacht oder als erledigt markiert. Abweichungen müssen begründet und abgestimmt werden.


## Zahlungsstatus – verbindliche Abgrenzung (R071)
Vertraglich fällige Monatsabschläge werden ohne gesonderten Zahlungsnachweis als angerechnete Zahlungen behandelt und reduzieren den offenen Betrag. Ein gespeicherter Abschlag der Art `advance` ersetzt den automatisch berechneten Betrag für seinen Monat; er wird nicht zusätzlich angerechnet. Buchungen der Art `payment` sind Sonderzahlungen und werden zusätzlich berücksichtigt. Die Dashboard-Zeile „Tatsächlich geleistete Abschläge“ entfällt. „Gesamt geleistete Zahlungen“ entspricht den angerechneten Abschlägen plus Sonderzahlungen. Die Buchungshistorie bleibt für Nachvollziehbarkeit und Sonderfälle erhalten.

## Vertragsassistent R067

Der Vertragsassistent besteht aus genau zwei Schritten. Schritt 1 erfasst Anbieter, Vertragsname/-nummer, Vertragsbeginn/-änderung, Abrechnungszeitraum-Beginn, Laufzeit in Monaten und ein davon unabhängiges Vertragsende. Das Abrechnungszeitraum-Ende wird aus Beginn und Laufzeit abgeleitet und gespeichert. Schritt 2 erfasst primären und optionalen sekundären Abrechnungsbereich sowie die zugehörigen Tarif-/Steuerwerte und schließt mit „Fertigstellen“ ab. Ein separater dritter Schritt entfällt.

## Abrechnungskarte R067

Verbrauch und Einspeisung werden in der Anzeige fachlich getrennt. Verbrauch weist Kosten, anteiligen Verbrauchsgrundpreis, Abschläge, Sonderzahlungen, Gutschriften, Gesamtkosten und offenen Betrag aus. Einspeisung weist Vergütung, Gesamtvergütung und offenes Guthaben aus; Verbrauchsgrundpreis und Verbrauchsabschläge sowie der Zahlungsbereich „Bereits gezahlt“ werden dort nicht dargestellt. Die zugrunde liegenden Buchungen und Zählerhistorien bleiben erhalten.

### Abschläge: Fälligkeit und Zahlung (aktualisierte Projektregel)

Jeder Monatserste innerhalb des Abrechnungszeitraums gilt automatisch als geleisteter vertraglicher Monatsabschlag. Eine manuelle Zahlungsbestätigung ist nicht erforderlich. Eine explizite, dem Zähler und der Abrechnungsrichtung zugeordnete Abschlagsbuchung ersetzt den automatischen Monatsbetrag dieses Monats, damit keine Doppelzählung entsteht. Zukünftige Monatserste werden nur als erwartete Zahlungen in der Prognose berücksichtigt und reduzieren den aktuellen Kontostand nicht.


## Kontostand und Anzeige (R071)
Der Kontostand verwendet das Vorzeichen aus Kundensicht: negative Werte sind Verbindlichkeiten, positive Werte Guthaben. Die Dashboard-Karte zeigt je nach Vorzeichen „Offener Betrag“, „Offenes Guthaben“ oder „Ausgeglichen“ und kennzeichnet diese Zustände rot, grün bzw. grau. Verbrauch und Einspeisung bleiben getrennte Konten.

Der jährliche Grundpreis steht in der Verbrauchskarte als grauer Klammerwert hinter „Anteiliger angefallener Grundpreis:“; der rechte Betrag ist der anteilige Grundpreis des Abrechnungszeitraums.


## R073 – Prognose-Grundfunktion

- Prognosen sind je logischem Zähler und Richtung separat aktivierbar.
- Verbrauch ist standardmäßig aktiv, Einspeisung standardmäßig deaktiviert.
- Jede aktivierte Richtung erhält eine Prognose des Periodenendsaldos und einen empfohlenen Monatsabschlag.
- Der Einspeiseabschlag ist ein eigener, tatsächlicher Brutto-Auszahlungsbetrag.
- Prognosen verändern weder Buchungen noch den aktuellen Kontostand.
- R073 verwendet zunächst die lineare Hochrechnung des bisherigen Periodendurchschnitts.


## R074 – Sichtbare Prognose in der Abrechnungskarte

Die Prognose wird in der Verbrauchs- bzw. Einspeisespalte unmittelbar unter dem offenen Betrag/Guthaben angezeigt. Der neutrale hellgraue Bereich verwendet dunkle Schrift. Der notwendige monatliche Abschlag ist die visuell wichtigste Kennzahl und wird groß und fett dargestellt. Der erwartete Abrechnungssaldo wird zusätzlich gezeigt. Saison-/Season-Auswahl und saisonale Prognosemodelle sind weiterhin offen.


## Monatsabschläge

Die Verwaltung erfolgt unter „Abrechnungen und Abschläge“. Nach Auswahl eines Stromzählers werden die Monate vom individuellen Abrechnungsbeginn bis einschließlich des aktuellen Home-Assistant-Monats angeboten. Zukünftige Monate erscheinen nicht. Verbrauch und Einspeisung werden getrennt bearbeitet. Die gespeicherten Monatswerte sind gemeinsame Berechnungsgrundlage für Kontostände und Prognosen.


## R109 – Globale Jahreszeiten und Prognose

- Jahreszeiten werden astronomisch und lokal anhand der Home-Assistant-Koordinaten bestimmt.
- Nord- und Südhalbkugel werden korrekt unterschieden; feste deutsche Kalendertage und Season-Integration sind nicht erforderlich.
- Die Oberfläche zeigt die berechnete Jahreszeit nur lesend an; eine manuelle Einstellung entfällt.
- Prognosesensoren aktualisieren sich beim Start, bei Quellwertänderungen und stündlich.
- Prognosefehler bleiben als Sensorattribute und ERROR-Protokolleinträge nachvollziehbar.
- Automatisierte Regressionstests prüfen die Ereignisgrenzen und beide Hemisphären.
