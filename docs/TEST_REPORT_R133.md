# Testbericht Beta R133

Datum: 26.11.2026

## Anlass

R132 blendete die Zuverlässigkeitszeile aus, wenn die Forecast-Sensoren die Zuverlässigkeitsattribute noch nicht bereitstellten. Außerdem wurde der gesamte Abschlagsbereich unterdrückt, wenn kein gültiger numerischer Abschlagswert vorlag.

## Änderungen

- Die Zuverlässigkeitszeile wird bei aktivierter Prognose immer gerendert.
- Solange die Berechnung als ausstehend gemeldet wird oder noch kein numerischer Wert verfügbar ist, erscheint „Wird ermittelt“ mit rotierendem Ladekreis.
- Sobald ein numerischer Zuverlässigkeitswert vorhanden und als verfügbar markiert ist, wird dieser angezeigt.
- Der Abschlagsbereich wird bei aktivierter Prognose immer gerendert: mit Betrag bei gültiger Empfehlung, andernfalls mit einer lokalisierten Erklärung.
- Verbrauchs- und Einspeisekarten verwenden dieselbe Renderlogik und beziehen ihre Werte weiterhin aus den jeweils getrennten Sensoren.

## Automatisierte Prüfungen

- pytest: 453 bestanden, 0 fehlgeschlagen.
- Python-Bytecode-/Syntaxprüfung (`compileall`): bestanden.
- JavaScript-Syntaxprüfung (`node --check`): bestanden.
- JSON-Validierung: 5 Dateien gültig.
- DE/EN-Übersetzungsschlüssel: gleiche Schlüsselstruktur.
- ZIP-Integritätsprüfung: nach Erstellung auszuführen.

## Nicht durchgeführt

- Kein vollständiger Home-Assistant-Laufzeittest.
- Kein visueller Browser-Test in einer realen Lovelace-Ansicht.
- Keine Prüfung gegen die produktive Datenbank des Nutzers.

Diese Punkte müssen nach Installation in Home Assistant praktisch geprüft werden.
