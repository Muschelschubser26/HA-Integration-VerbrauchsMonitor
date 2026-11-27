# Testbericht Beta R136

## Umfang
- Neuer Menüpunkt `Monatsabschlag ändern` in der Reihenfolge Buchungen verwalten, Monatsabschlag ändern, Monatsabschläge bearbeiten.
- Stromzählerauswahl und automatische Übernahme des Abrechnungsbereichs bei genau einer verfügbaren Richtung.
- Auswahl eines Wirksamkeitsmonats ab dem Folgemonat bis zum Ende des Abrechnungszeitraums.
- Speicherung des neuen Betrags ab dem ausgewählten Monat bis zum Periodenende über die bestehende revisionssichere Monatsabschlagsverwaltung.
- Anzeige des aktuellen Abschlags sowie des Gültigkeitsdatums bei bereits erfasster manueller Änderung.
- Deutsche und englische UI-Texte.

## Automatisierte Prüfungen
- `pytest -q`: **470 bestanden**.
- Python-AST-/Kompilierungsprüfung: erfolgreich.
- JavaScript-Syntaxprüfung (`node --check`): erfolgreich.
- JSON-Validierung für `strings.json`, `translations/de.json` und `translations/en.json`: erfolgreich.
- Deutsche und englische Übersetzungsstruktur: 189 Blatt-Schlüssel je Sprache, synchron.
- Menüreihenfolge: erfolgreich geprüft.

## Nicht durchgeführte Prüfungen
- Kein vollständiger Home-Assistant-Laufzeittest.
- Kein echter UI-Test des mehrstufigen Dialogs im Browser.
- Keine Live-Prüfung einer anschließenden Kontostandsaktualisierung in einer laufenden HA-Instanz.

Diese Laufzeitprüfungen müssen nach Installation in Home Assistant erfolgen.
