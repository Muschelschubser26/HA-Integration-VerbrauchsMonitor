# Beta R126 Test Report

## Automated validation

- Unit and regression tests: **417 passed**.
- Python compilation: passed for all integration Python modules.
- JavaScript syntax: passed with `node --check`.
- JSON syntax: passed for all JSON files.
- German and English translation key parity: passed by the project test suite.
- Fixed numeric reference scenarios for billing, tariffs, payments, solar profiles, and forecast recommendations remain covered.
- ZIP archive integrity and required project structure: passed.

## R126 UI changes

- Forecast reliability is placed directly above the forecast heading, after the season label.
- Current consumption/feed-in text is slightly larger (10px), has an 8px label/value gap, and retains a right-aligned Watt value.
- One thin divider is drawn below the combined billing-period progress/current-power row and above the tariff row.
- The tariff row remains without a thin bottom divider because the thicker finance-section divider follows it.

## Runtime verification boundary

No live Home Assistant instance or browser session was available in the build environment. The tests verify source structure, syntax, deterministic domain calculations, and archive contents; they do not prove the rendered appearance in the target Home Assistant frontend. The two-column compass-direction checkbox layout also remains outstanding and is not claimed as implemented in R126.
