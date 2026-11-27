# Release-Prüfstatus – 0.0.1

## Im Paket korrigiert

- Repository-Links auf `Muschelschubser26/HA-Integration-VerbrauchsMonitor` vereinheitlicht.
- `manifest.json` und `pyproject.toml` auf Version `0.0.1` vereinheitlicht.
- README auf die freigegebene GitHub-Darstellung umgestellt und vier Home-Assistant-Screenshots ergänzt.
- Installationsanleitung auf den enthaltenen Funktionsstand aktualisiert.
- Zuverlässigkeitsdokumentation an die implementierte historische Bewertungsgrundlage angepasst.
- Regressionstest für die offizielle Dokumentations-URL aktualisiert.

## Unverändert übernommen

- `CHANGELOG.md` wurde bewusst nicht verändert.
- Integrations-Berechnungslogik und bestehende Konfigurations-/Datenbanklogik wurden nicht geändert.
- Die offenen Laufzeitpunkte in `OFFENE_PUNKTE.md` bleiben offen.

## Automatisierte Prüfung

- Python-Test-Suite: 585 Tests bestanden (lokaler Paketlauf).
- JSON-Dateien: syntaktisch gültig.
- JavaScript-Syntax: separat zu prüfen bzw. in diesem Paketlauf nicht als Home-Assistant-Frontend-Laufzeittest zertifiziert.
- ZIP-Integrität: nach Erstellung erneut geprüft.

## Noch keine uneingeschränkte Produktionsfreigabe

Die folgenden Prüfungen benötigen das echte Zielsystem und können nicht aus dem ZIP allein bestätigt werden:

- Home-Assistant-Start, Reload und Unload.
- Recorder-Executor und reale Recorder-Historie.
- Entity-Registry-Migrationen und Anzeigenamen.
- Mitternachtswechsel, Neustart und Zählerwechsel bei Tageswertsensoren.
- Lovelace-Ressourcenregistrierung und visuelle Kartenprüfung.
- SQLite-Migration und Wiederherstellung mit realen Bestandsdaten.

Diese Punkte sind weiterhin in `docs/OFFENE_PUNKTE.md` dokumentiert. Das Paket ist strukturell und automatisiert geprüft, aber diese Laufzeitprüfungen müssen vor einer uneingeschränkten Produktionsfreigabe im Zielsystem durchgeführt werden.
