# Beta R127 Test Report

## Scope

R127 applies the approved forecast-card order and makes intentionally suppressed monthly advance recommendations understandable. The domain rule itself remains conservative: no new monthly recommendation is generated when fewer than two future payment dates remain, and no recommendation is generated when scheduled and booked payments already cover the forecast amount.

## Changes verified

- Forecast card order: season, forecast end-date heading, reliability directly below the heading, expected billing balance, then recommendation or an explanatory note.
- German and English explanations for final payment period, no remaining payment gap, and insufficient measured reliability.
- Generic localized fallback explanation when the recommendation is unavailable for another reason.
- Forecast sensor propagates `insufficient_reliability` when the mathematical recommendation is otherwise possible but measured reliability is not yet available.
- `advance_recommendation_final_period_protection` now reports the actual `months_remaining < 2` protection state.

## Automated validation

- Python unit and regression tests: 421 passed.
- Python bytecode compilation: passed.
- JavaScript syntax check: passed.
- JSON parsing: passed.
- German/English translation structure parity: passed.
- ZIP archive integrity and required project structure: passed.

## Not performed

No live Home Assistant Core instance, actual Recorder database, or browser session was available. Therefore sensor setup time, live entity availability, runtime forecast updates, and final visual rendering must still be verified after installation. The requested two-column compass-direction checkbox presentation remains outstanding; the native config-flow selector does not expose a supported two-column layout option.
