# Test Report – VerbrauchsMonitor Beta R131

## Scope

R131 fixes the persistent zero values in the feed-in monthly-advance editor. The user confirmed that no feed-in month had intentionally been set to `0.00 €`, allowing the historical erroneous zero overrides from the earlier editor defect to be migrated safely.

## Root cause

R128/R129 could save the feed-in monthly editor's incorrect `0.00 €` defaults as monthly override records with `source="manual"`. R130 treated manual zero overrides as intentional and therefore returned those zeros instead of falling back to the positive contract amount. The previous fallback was not sufficient because the accidental legacy rows had already been labelled as manual.

## Changes

- Added a one-time SQLite snapshot migration, scoped to the selected meter and contract.
- The latest active zero override per month is superseded and replaced with the contract's gross feed-in payout amount.
- Historical records are retained and linked through `supersedes`; replacement rows include a migration source and explicit reason.
- A persistent per-meter/per-contract marker prevents the repair from running again. Future user-entered zero values therefore remain valid.
- Contract net values are converted to gross with the configured VAT rate. Legacy feed-in-only contracts can fall back to their previous generic monthly-advance field.
- The repair runs before the editor form is displayed, and the database snapshot is reloaded after a successful migration.
- Consumption records, other meters/contracts, and nonzero feed-in overrides are not changed.

## Automated tests

- Full test suite: **449 passed**.
- Dedicated R131 regression tests: **4 passed**.
- Tests cover gross contract default restoration, audit-history preservation, one-time/idempotent behavior, future intentional zero preservation, scope isolation, nonzero preservation, and invocation from the editor flow.
- Python compilation: passed.
- JavaScript syntax check: passed.
- JSON validation: passed.
- German/English translation parity: passed.
- ZIP archive integrity and project structure: passed.

## Fixed-value reference case

Given a feed-in contract monthly payout of `136.00 €` gross and legacy active monthly override records of `0.00 €` for January and February, opening the editor migrates both months to `136.00 €`. Both prior zero records remain in history and are marked superseded. Re-running the migration does not change the records. A new zero override entered after the migration remains `0.00 €`.

## Validation boundary

The actual Home Assistant instance and its live database are not available in this build environment. The migration is tested against the integration's SQLite persistence layer using isolated temporary databases. A live Home Assistant installation/restart and inspection of the user's actual monthly editor remain necessary for runtime acceptance.
