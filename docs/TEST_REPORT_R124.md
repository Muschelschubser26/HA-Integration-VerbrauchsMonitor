# Beta R124 Test Report

## Automated validation

- Unit and regression tests: **409 passed**.
- Python compilation: passed for all integration Python modules.
- JavaScript syntax: passed with `node --check`.
- JSON syntax: passed for all JSON files.
- German and English translation key parity: passed by the project test suite.
- Fixed numeric reference scenarios: passed, including cent-exact cost, base-price, payment, balance, and monthly-recommendation cases.
- Solar reference scenarios: passed for winter/summer consumption profile changes, local sunrise/sunset in `Europe/Berlin`, selected feed-in orientations, and history-based solar adjustments in both directions.
- Recommendation safety: passed for final-payment-month suppression, positive credit with one payment date, and deduction of scheduled future payments before recommendation calculation.
- ZIP integrity and required integration directory structure: checked during packaging.

## Key fixed-reference recommendation case

For the fixed 2026-10-23 reference case with a 2026-07-01 billing start, six-month billing period, €544.00 forecast value, no booked advances, and €400.00 scheduled future advances, two future payment dates remain. The recommendation is **€72.00 per month** (`(544.00 - 400.00) / 2`).

When only one future payment date remains, the monthly recommendation is **unavailable**, not a one-month spike. If no positive payment gap remains after booked and scheduled payments, no recommendation is shown.

## Solar model behavior

- Consumption profiles use local season, solar elevation/azimuth, daylight duration, and bounded low-sun/short-day demand adjustment.
- Feed-in profiles use local solar geometry and the configured multiple compass directions.
- History-based future projections retain observed monthly rates as the primary evidence and apply a bounded astronomical adjustment only to the future portion.
- Sunrise and sunset are calculated locally from Home Assistant coordinates and timezone.

## Known limitation

The two-column compass-direction checkbox layout remains unimplemented. The Home Assistant native config-flow selector supports multiple selection but has no supported column-layout option; a dedicated custom config-flow frontend is required.

## Runtime verification boundary

No live Home Assistant installation was available. Integration startup/reload, Recorder statistics, sensor availability, entity-registry migration, config-flow visual layout, and browser rendering must still be verified in the target installation. Automated tests do not replace this runtime test.
