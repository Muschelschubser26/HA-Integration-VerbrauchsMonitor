# Test Report – VerbrauchsMonitor Beta R129

## Scope

Review and correction of tariff precision, forecast energy valuation, exact billing-period horizon, base-price accrual, advance schedules, account adjustments, and reliability initialization expiry.

## Findings and fixes

- The displayed feed-in tariff had been rounded to two decimals while the ledger correctly used the stored exact gross tariff. `28.74 ct/kWh` net at 19% VAT is `34.2006 ct/kWh` gross; for `5,382.059 kWh`, the correct amount is `1,840.70 €`. The card now displays up to six tariff decimals when needed.
- Forecast energy kWh already used history, season, solar position, sunrise/sunset, and per-meter orientation, but the monetary forecast then recalculated future costs from a separate linear daily average. The monetary forecast now values the model-projected remaining kWh directly.
- The forecast previously used date-only elapsed periods and could double-count the current day in the history-based projection. It now receives the exact local instant and includes only the unmeasured part of today through the complete final billing day.
- Base-price accrual in the forecast used whole calendar months. It now uses the same continuous elapsed-time helper as the live balance, with DST/leap-year-aware elapsed seconds and a fixed period-end boundary.
- Forecast balances now include additional payments, credits, and signed corrections. Corrections are no longer added to recurring extra charges. One-off extra charges are counted once and are not extrapolated over the remaining period.
- Future feed-in monthly advances now include configured VAT and use month-specific overrides or the actual contract default.
- Fixed the feed-in monthly-advance editor's zero-default bug: R128 read the default from the meter object, although the canonical feed-in advance is stored on the contract. R129 reads `contract.feed_in_monthly_advance`, converts the stored net amount to gross with the contract VAT, and displays it exactly like the consumption editor.
- Legacy feed-in zero entries without provenance (which could have been saved from R128's erroneous zero defaults) now fall back to the configured non-zero contract amount. Newly saved monthly entries are marked `source=manual`, so an intentionally entered `0.00 €` remains authoritative. Superseded entries are ignored.
- Added regression coverage for the gross conversion (`136.00 €`), contract fallback, legacy zero recovery, explicit manual zero, and monthly override precedence.
- The provisional reliability value expires after six hours. Thereafter the value is based on at least five completed hourly evaluations or qualifying history; otherwise the card says reliability is being determined.
- An explicitly empty compass-direction selection uses the neutral four-direction model consistently in history-based feed-in forecasts.

## Fixed reference values from the screenshot

Using the screenshot snapshot (25 November 2026, approximately 23:56 local), visible readings, and inferred tariff/payment settings:

| Item | Verified calculation |
|---|---:|
| Feed-in gross tariff | `28.74 × 1.19 = 34.2006 ct/kWh` |
| Feed-in remuneration | `5,382.059 × 0.342006 € = 1,840.70 €` |
| Consumption energy cost | `1,860.851 × 0.2828 € = 526.25 €` |
| Consumption accrued base price | continuous time-prorated value; exact runtime value depends on the current timestamp and DST offset |
| Consumption forecast balance | recalculated with the signed `-66.00 €` correction and the remaining December advance |
| Feed-in forecast balance | recalculated with the gross December advance (`136.00 €`) rather than its net value |

The resulting forecast balances are not claimed as exact values for the live installation because the screenshot does not expose the complete Recorder history, exact tariff storage values, or every booking. The fixed tests verify the formulas and sign handling independently.

## Tests and validation

- Full automated test suite: **441 passed**.
- Python compilation: passed.
- JavaScript syntax check: passed.
- Exact tariff arithmetic, exact time horizon, partial-day seasonal projection, signed account adjustments, one-off charges, reliability expiry, neutral orientation, and direction-sensitive monetary forecasts have dedicated regression tests.
- A live Home Assistant startup, actual Recorder query, entity-state timing test, and browser visual verification were not available in this environment.

## Release status

Beta R129 is packaged from the reviewed working copy. Automated checks passed; a full Home Assistant runtime test against the user's live database and browser remains outstanding.
