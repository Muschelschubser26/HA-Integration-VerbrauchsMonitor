# VerbrauchsMonitor

Home-Assistant-Custom-Integration zur lokalen Verwaltung von Stromzählern, Verträgen, Tarifen, Abrechnungen, Zahlungen und Verbrauchs-/Einspeiseprognosen.

**Projektkennung:** `ha-verbrauchsmonitor`  
**Integration-Domain:** `verbrauchsmonitor`  
**SemVer:** `0.0.2`  
**Paketstand:** `Beta R113`

Deutsch ist die Standardsprache. Die Oberfläche unterstützt zusätzlich Englisch und richtet sich nach der in Home Assistant eingestellten Sprache. Die Verarbeitung und Speicherung erfolgen lokal in Home Assistant. Es gibt keine ungefragte Cloud-Kommunikation oder Telemetrie.

## Funktionsumfang

- Mehrere logische Stromzähler und mehrere Verträge innerhalb einer Integration.
- Optionale Zuordnung von Verbrauchs- und Einspeisezählerständen sowie optionalen Leistungs- und Außenhelligkeitsentitäten.
- Getrennte Abrechnungsrichtungen für Strombezug und Einspeisung.
- Vertrags- und Tarifverwaltung mit Netto-/Brutto-Eingaben, konfigurierbarer Mehrwertsteuer und getrennten Preisarten.
- Abrechnungsperioden, Anfangszählerstände und Herkunfts-/Änderungshistorie der Anfangswerte.
- Lokale Buchungsverwaltung für Abschläge, Sonderzahlungen, Gutschriften und Korrekturen.
- Getrennte Kontostände für Verbrauch und Einspeisung.
- Prognosen je Quellzähler und Abrechnungsrichtung; saisonale Gewichtung wird nur bei ausreichender Recorder-Historie und Datenqualität verwendet.
- Eigene Lovelace-Abrechnungskarte mit Auswahl von logischem Zähler und Abrechnungsrichtung.
- Datenbankstatus, Optimierung, Import/Export und Reset-Funktionen über die Integrationsoberfläche.

Die konkrete Verfügbarkeit einzelner Eingabefelder und Anzeigen richtet sich nach der Konfiguration. Nicht konfigurierte optionale Datenquellen werden nicht als gültige Messwerte ersetzt.

## Voraussetzungen

- Home Assistant Core **2026.11.1 oder neuer** (Projektziel gemäß `hacs.json`; tatsächliche Kompatibilität muss in der Zielinstallation geprüft werden).
- Eine oder mehrere Home-Assistant-Sensorentitäten für Zählerstände. Leistungswerte und Außenhelligkeit sind optional.
- Für saisonale Prognosen werden geeignete Recorder-Langzeitstatistiken oder ausreichend vorhandene Detailhistorie benötigt.

Die Integration hat keine zusätzlichen Python-Laufzeitabhängigkeiten außerhalb der von Home Assistant bereitgestellten Umgebung (`manifest.json`: `requirements` ist leer).

## Installation

### Manuelle Installation

1. Vor dem Update ein Home-Assistant-Backup erstellen.
2. Den Ordner `custom_components/verbrauchsmonitor/` aus diesem Projekt nach `/config/custom_components/verbrauchsmonitor/` kopieren.
3. Einen vorhandenen Integrationsordner vollständig ersetzen; keine alten Dateien im Ordner zurücklassen.
4. Home Assistant vollständig neu starten.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **VerbrauchsMonitor** suchen und die Einrichtung starten.
6. Nach dem Anlegen die Integrationsoptionen öffnen, um weitere Verträge, Zähler, Abrechnungen, Buchungen und Prognosen zu verwalten.

### Lovelace-Karte

Im Lovelace-Storage-Modus registriert die Integration die Kartenressource. Anschließend das Dashboard bzw. den Browser neu laden und über **Karte hinzufügen** nach **VerbrauchsMonitor** suchen. Im YAML-Ressourcenmodus muss folgende Ressource als Modul eingebunden sein:

`/verbrauchsmonitor/verbrauchsmonitor-card.js`

Die Karteninstanz wird für einen logischen Zähler und eine Abrechnungsrichtung (Verbrauch oder Einspeisung) konfiguriert. Weitere Zähler oder Richtungen benötigen jeweils eine eigene Karteninstanz.

## Konfiguration und Bedienung

Die Ersteinrichtung erfolgt über den Config Flow. Nachträgliche Änderungen werden über den Options Flow der Integration vorgenommen.

- **Verträge:** Vertragsbezeichnung und -daten, Abrechnungszeitraum, Arbeitspreis bzw. Einspeisevergütung, Grundpreis, Mehrwertsteuer und vereinbarte Abschläge.
- **Zähler:** Logischer Zählername, optionale Zählernummer sowie Quellentitäten für Bezug und Einspeisung.
- **Abrechnungen:** Abrechnungsanfang, Zählerstand-Baselines und Abrechnungswerte.
- **Buchungen:** Sonderzahlungen, Gutschriften und Korrekturen mit Zuordnung zu Zähler und Abrechnungsrichtung.
- **Monatsabschläge:** Monatliche Werte können je Zähler und Abrechnungsrichtung gepflegt werden.
- **Prognose:** Verbrauchs- und Einspeiseprognosen können getrennt aktiviert und zugeordnet werden.
- **Datenverwaltung:** Datenbankinformationen, Optimierung, Export/Import und bestätigungspflichtige Reset-Aktionen.

### Abschlags- und Kontostandslogik

Ein vertraglich vereinbarter monatlicher Abschlag wird am Monatsersten innerhalb des jeweiligen Abrechnungszeitraums automatisch als geleistet berücksichtigt. Eine manuelle Zahlungsbestätigung ist dafür nicht erforderlich. Eine explizit zugeordnete Abschlagsbuchung ersetzt den automatischen Betrag desselben Monats, damit keine Doppelzählung entsteht. Verbrauchs- und Einspeisungsabschläge werden getrennt verarbeitet. Zukünftige Monatserste werden in Prognosen als erwartete Zahlungen behandelt und verändern den aktuellen Kontostand nicht.

Gutschriften und Korrekturen werden als eigenständige, nachvollziehbare Buchungen gespeichert. Die Kontostände folgen der Kundensicht: negative Werte stehen für eine Verbindlichkeit, positive Werte für ein Guthaben.

## Speicherung und Datenschutz

Die Integrationskonfiguration liegt in den Home-Assistant-Config-Entry-Daten. Fachliche Buchungen und weitere persistente Integrationsdaten werden lokal im Home-Assistant-Speicher verwaltet. Die Datenbankfunktionen verwenden einen integrationsspezifischen JSON-Datenspeicher; der konkrete Pfad wird durch `database.py` bestimmt.

Es werden keine Zugangsdaten für externe Dienste benötigt. Es findet keine automatische Telemetrie und keine ungefragte Übertragung von Mess- oder Vertragsdaten statt. Vor Reset- oder Importvorgängen die angezeigten Hinweise beachten und vor größeren Änderungen ein Home-Assistant-Backup erstellen.

## Updates und Neustart

- Änderungen an Python-Dateien, `manifest.json` oder Abhängigkeiten: Home Assistant vollständig neu starten.
- Änderungen ausschließlich an der Lovelace-JavaScript-Karte: Dashboard/Browser neu laden; gegebenenfalls Browser-Cache aktualisieren.
- Änderungen an Integrationsoptionen: Speichern verwendet den Config-Entry-Reload.

Ein Config-Entry-Reload importiert geänderte Python-Module nicht neu und ersetzt daher keinen vollständigen Home-Assistant-Neustart nach einem Code-Update.

## Dokumentation und Tests

- `docs/ARCHITEKTUR.md`: Komponenten, Datenfluss und Speicherverantwortung.
- `docs/INSTALLATION.md`: Installations- und Bedienhinweise.
- `docs/UPDATE_UND_RELOAD.md`: Update- und Reload-Verhalten.
- `docs/ANFORDERUNGEN.md`: Anforderungsliste und Umsetzungsstatus.
- `docs/OFFENE_PUNKTE.md`: bekannte Grenzen und erforderliche Zielsystemprüfungen.
- `tests/`: automatisierte Unit- und Regressionstests.

Automatisierte Tests sind Bestandteil der Entwicklungsprüfung. Ein erfolgreicher automatisierter Testlauf ersetzt keinen vollständigen Laufzeittest in einer realen Home-Assistant-Installation.

## Lizenz und Kontakt

Dem Paket liegt eine `LICENSE`-Datei mit MIT-Lizenztext bei. Die rechtliche Freigabe dieser Lizenz durch den Rechteinhaber ist vor einer öffentlichen Veröffentlichung separat zu bestätigen.

Support: **Support@gehtdoch.eu**
