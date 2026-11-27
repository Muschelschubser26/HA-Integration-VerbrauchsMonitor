# Testbericht VerbrauchsMonitor Beta R160

## Umfang

- Korrektur der Tageswert-Anzeigenamen, damit Home Assistant den Namen nicht auf den Gerätepräfix-Rest `(heute)` verkürzt.
- Sichere Migration bekannter automatisch erzeugter Registry-Platzhalter; individuelle Namen bleiben erhalten.
- Robuste Tagesbasis: zuerst Recorder-Zustand, danach Langzeitstatistik; wenn beides nicht verfügbar ist, realer aktueller Zählerstand als persistente Teil-Tagesbasis.
- Kennzeichnung `partial_day` wird gespeichert und nach Neustart wiederhergestellt. Der Tageswert steigt ab dieser realen Basis mit dem kumulierten Quellzähler.
- Energie-Metadaten bleiben `device_class=energy`, `state_class=total_increasing`, Einheit kWh.

## Automatisierte Prüfungen

- Pytest: **547 bestanden**.
- Python-Bytecode-Kompilierung: durchgeführt.
- JavaScript-Syntaxprüfung: durchgeführt.
- Sämtliche JSON-Dateien: gültig.
- Deutsche und englische Übersetzungsdateien: gültig und identischer Schlüsselbestand (273/273).
- ZIP-Integrität und vollständige Projektstruktur: geprüft.

## Gezielte R160-Regressionstests

- Die Namen lauten `Tagesverbrauch (heute)` und `Tages-Einspeisung (heute)` und enthalten nicht den identischen Präfix des jeweiligen Geräts.
- Nur bekannte automatisch erzeugte Altbezeichnungen werden migriert; eigene Namen bleiben bestehen.
- Bei fehlender Recorder-/Statistikbasis wird der reale aktuelle Zählerstand als Teil-Tagesbasis verwendet, niemals ein erfundener Messwert.
- Die Tagesdifferenz steigt bei steigenden kumulierten Quellständen, bleibt nach Wiederherstellung derselben gespeicherten Basis identisch und wird bei einer neuen Mitternachtsbasis wieder null.
- Die Teil-Tageskennzeichnung wird zusammen mit dem Baselinewert gespeichert.

## Nicht durchführbare Laufzeitprüfungen

Home Assistant ist in der Build-Umgebung nicht installiert. Deshalb konnten die echte Entity Registry, der tatsächliche Geräteansicht-Renderer, Recorder-Abfragen, der Mitternachts-Event-Loop und Langzeitstatistiken nicht live ausgeführt werden. Diese Punkte bleiben als Praxistests offen. Die automatisierten Tests prüfen die Integrationslogik und Regressionen, ersetzen aber keinen Home-Assistant-Laufzeittest.
