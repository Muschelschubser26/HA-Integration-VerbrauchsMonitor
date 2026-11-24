# Bekannte Grenzen und noch erforderliche Prüfungen

Dieses Dokument trennt bekannte fachliche Einschränkungen von Prüfungen, die nur in den tatsächlichen Zielsystemen durchgeführt werden können.

## Fachliche und funktionale Grenzen

1. **Physische Zählerwechsel:** Die vollständige Historie beliebig vieler physischer Zählerwechsel mit Segmentdifferenzen, lückenloser Audit-Historie und nachträglicher Korrektur ist noch nicht vollständig umgesetzt.
2. **Zeitliche Preisgültigkeit:** Preisänderungen innerhalb eines Abrechnungszeitraums werden noch nicht vollständig zeitanteilig aufgeteilt. Eine vollständige Tarifgültigkeitshistorie und unveränderliche Abrechnungssnapshots stehen noch aus.
3. **Grundpreis Einspeisung:** Ein eigenständiger Grundpreis für Einspeisung ist nicht als separater Vertragsbestandteil modelliert.
4. **Datenexport:** Konfiguration in Config-Entry-Optionen und fachliche Daten im lokalen JSON-Datenspeicher sind getrennte Speicherbereiche. Ein gemeinsamer vollständiger Export/Import beider Bereiche ist noch nicht umgesetzt.
5. **Abrechnungsbereiche:** Der aktuelle Vertrags-/Zähleraufbau unterstützt die vorgesehenen Verbrauchs- und Einspeisungsrichtungen. Ein vollständig frei definierbares Modell beliebig vieler Abrechnungsbereiche ist nicht umgesetzt.
6. **Saldo und Messwerte:** Ein ungültiger Zählerrückgang wird nicht als Verbrauch interpretiert. In diesem Fall kann der daraus abgeleitete Kontostand nicht berechnet werden und muss fachlich geprüft werden.

## Prüfungen in der Home-Assistant-Zielinstallation

Die Home-Assistant-Zielsystemtests wurden laut Projektbetreiber erfolgreich durchgeführt. Die Ergebnisse beziehen sich auf die vom Betreiber getestete Installation und ersetzen keine Prüfung in abweichenden Home-Assistant-Versionen oder individuellen Installationen.

## Repository- und Veröffentlichungsangaben

1. Das `documentation`-Feld in `manifest.json` verweist auf das öffentliche GitLab-Production-Repository. Bei einer späteren Änderung der kanonischen Repository-Adresse muss dieser Eintrag entsprechend aktualisiert werden.
2. Die MIT-Lizenz ist vom Projektinhaber für die öffentliche Beta-Veröffentlichung freigegeben.
3. Die Git-Commit-Historie ist nicht Bestandteil des ZIP-Archivs. Sie muss separat vor dem ersten öffentlichen Commit auf früher gespeicherte Zugangsdaten, Tokens, private IP-Adressen und persönliche Daten geprüft werden.

