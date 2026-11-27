<p align="center">
  <img src="assets/verbrauchsmonitor-banner.png" alt="VerbrauchsMonitor – Smarte Energieübersicht" width="100%">
</p>

<p align="center">
  <a href="#funktionen">Funktionen</a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#installation">Installation</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="docs/">Dokumentation</a> ·
  <a href="https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor/issues">Fehler melden</a>
</p>

<h1 align="center">VerbrauchsMonitor</h1>

<p align="center">
  <strong>Stromverbrauch, Einspeisung, Abrechnung und Energie-Forecast direkt in Home Assistant im Blick.</strong><br>
  Lokale Datenhaltung · Deutsche und englische Oberfläche · Keine Cloud-Telemetrie
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.0.1-blue">
  <img alt="Home Assistant" src="https://img.shields.io/badge/Home%20Assistant-2026.11.1%2B-18BCF2">
  <img alt="License" src="https://img.shields.io/github/license/Muschelschubser26/HA-Integration-VerbrauchsMonitor">
</p>

Der **VerbrauchsMonitor** ist eine Custom Integration für Home Assistant zur lokalen Verwaltung und Auswertung von Stromzählern. Er verbindet Messwerte für Verbrauch und Einspeisung mit Vertrags- und Tarifdaten, Abrechnungszeiträumen, Zahlungen, Kontoständen und Energieprognosen.

**Repository:** [Muschelschubser26/HA-Integration-VerbrauchsMonitor](https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor)  
**Domain:** `verbrauchsmonitor`  
**Produktivversion:** `0.0.1`  
**Entwicklungsbasis:** `0.0.2-beta.1` · interne Revision `R0171`  
Frühere Beta-Stände, darunter Beta R161, sind im Changelog dokumentiert.

Die Verarbeitung und Speicherung erfolgen lokal in Home Assistant. Die Integration initiiert keine Cloud-Kommunikation und sendet keine Telemetrie.

---

## Funktionen

<div align="center">

| Zähler und Messwerte | Verträge und Abrechnung |
|:--|:--|
| Verbrauchs- und Einspeisezähler | Verträge, Tarife und Abrechnungszeiträume |
| Tages-, Wochen-, Monats- und Jahreswerte | Monatsabschläge und einzeln änderbare Monatsbeträge |
| Aktuelle Leistung und Energieverläufe | Buchungen, Zahlungen und Kontostände |
| Mehrere logische Zähler und Richtungen | Abrechnungs- und Prognoseübersichten |

| Prognose und Zuverlässigkeit | Datenverwaltung |
|:--|:--|
| Verbrauchs- und Einspeiseprognosen | Lokale SQLite-Datenbank |
| Saison-, Tageszeit- und Sonnenpositionsbezug | Datenbankinformationen und Sicherungsgrundlagen |
| Getrennte Bewertung für Verbrauch und Einspeisung | Recorder-Entitäten als YAML exportieren |
| Transparente Zuverlässigkeitsanzeige | Migrations- und Diagnoseinformationen |

</div>

## Screenshots

Die folgenden Ansichten stammen aus Home Assistant und zeigen die Karten des VerbrauchsMonitors.

<table>
  <tr>
    <td width="50%" align="center">
      <img src="assets/Stromzähler-Verbrauch.PNG" alt="Verbrauchszählerkarte" width="100%">
      <br><strong>Verbrauchszählerkarte</strong>
    </td>
    <td width="50%" align="center">
      <img src="assets/Stromzähler-Einspeisung.PNG" alt="Einspeisezählerkarte" width="100%">
      <br><strong>Einspeisezählerkarte</strong>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="assets/Summenzähler-Verbrauch.PNG" alt="Summenzähler Verbrauch" width="100%">
      <br><strong>Summenzähler – Verbrauch</strong>
    </td>
    <td width="50%" align="center">
      <img src="assets/Summenzähler-Einspeisung.PNG" alt="Summenzähler Einspeisung" width="100%">
      <br><strong>Summenzähler – Einspeisung</strong>
    </td>
  </tr>
</table>

## Installation

### Voraussetzungen

- Home Assistant Core **2026.11.1 oder neuer**
- Mindestens ein gültiger Quellzähler als Home-Assistant-Sensor
- Für historische Prognosegrundlagen: verfügbare Recorder-Historie bzw. Langzeitstatistiken

### Installation über HACS

1. HACS öffnen und zu **Integrationen** wechseln.
2. Über das Menü **Benutzerdefinierte Repositories** öffnen.
3. Repository-URL eintragen:  
   `https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor`
4. Kategorie **Integration** auswählen und hinzufügen.
5. Nach „VerbrauchsMonitor“ suchen und die Integration installieren.
6. Home Assistant vollständig neu starten.
7. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** den VerbrauchsMonitor auswählen und konfigurieren.

### Manuelle Installation

1. Vor Änderungen ein vollständiges Home-Assistant-Backup erstellen.
2. Den Ordner `custom_components/verbrauchsmonitor/` aus diesem Paket vollständig nach `/config/custom_components/verbrauchsmonitor/` kopieren. Den alten Integrationsordner vollständig ersetzen, nicht Dateien zusammenführen.
3. Home Assistant vollständig neu starten.
4. Den VerbrauchsMonitor unter **Einstellungen → Geräte & Dienste** hinzufügen bzw. konfigurieren.
5. Nach dem Neustart das Dashboard neu laden.

Details und Updatehinweise stehen in der [Installations- und Updateanleitung](docs/INSTALLATION.md).

## Wichtige Hinweise

- Monatsabschläge können je Monat einzeln bearbeitet werden. Der laufende Vertragsabschlag wird dadurch nicht automatisch fortgeschrieben.
- Die Auswahl für zukünftige Monatsbeträge beginnt beim nächsten Monat und umfasst höchstens sieben zulässige Monate. Jahreswechsel werden berücksichtigt; die Änderung gilt innerhalb des Abrechnungszeitraums bis zu dessen Ende.
- Die Zuverlässigkeitsanzeige basiert auf tatsächlich verfügbaren historischen Daten. Bei unzureichender Recorder-Historie wird kein künstlicher Prozentwert erzeugt.
- Die Zuverlässigkeit ist eine datenbasierte Einschätzung und keine Garantie für die Höhe einer späteren Abrechnung.

## Dokumentation und Support

- [Installations- und Updateanleitung](docs/INSTALLATION.md)
- [Architektur](docs/ARCHITEKTUR.md)
- [Anforderungen](docs/ANFORDERUNGEN.md)
- [Datenbankmigration](docs/DATENBANK_MIGRATION_R169.md)
- [Zuverlässigkeitsmodell](docs/ZUVERLAESSIGKEIT.md)
- [Changelog](CHANGELOG.md)
- [Offene Punkte und Laufzeitprüfungen](docs/OFFENE_PUNKTE.md)
- [Fehler melden / Fragen stellen](https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor/issues)

---

## ☕ Entwicklung unterstützen

Gefällt dir der VerbrauchsMonitor und hilft dir die Integration bei der Übersicht über deinen Energieverbrauch?

Wenn du die Weiterentwicklung unterstützen möchtest, freue ich mich über einen Kaffee. Deine Unterstützung hilft dabei, neue Funktionen zu entwickeln, Verbesserungen umzusetzen und die Integration weiter zu pflegen.

<p align="center">
  <a href="https://buymeacoffee.com/muschelschubser26">
    <img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support%20Development-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee">
  </a>
</p>

<p align="center">
  Vielen Dank für deine Unterstützung! ❤️
</p>

---

<p align="center">
  <strong>VerbrauchsMonitor</strong><br>
  Smarte Energieübersicht – lokal in Home Assistant.
</p>
