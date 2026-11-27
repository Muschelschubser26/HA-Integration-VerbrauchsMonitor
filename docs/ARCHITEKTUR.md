# Technical Architecture

## Architecture principles

- Home Assistant integration, domain logic, persistence, and frontend remain separate.
- One hub config entry manages multiple contracts and logical meters.
- `consumption` and `feed_in` are independent accounting directions.
- Persistent identifiers are language-independent and are not derived from translated labels.
- All normal processing and persistence are local; there is no unsolicited telemetry.

## Module responsibilities

| Module | Responsibility |
|---|---|
| `__init__.py` | Config-entry lifecycle, card registration, registry migration/cleanup, services, and baseline capture |
| `config_flow.py` | Initial setup and options flow for contracts, meters, monthly advances, bookings, forecasts, and data management |
| `const.py` | Domain, configuration keys, platforms, and role definitions |
| `sensor.py` | Home Assistant entities, source mirroring, balance calculation, and forecast attributes |
| `database.py` | Local SQLite persistence, validation, bookings, monthly advances, import/export, backup, and reset |
| `ledger.py` | Booking and balance logic, including monthly advance allocation |
| `pricing.py` | Decimal-based tariff and tax calculations |
| `forecast.py` | Billing-period forecast projection and reliability compatibility |
| `forecast_model.py` | Local solar calculations, generic first-install profiles, immutable hourly forecast records, evaluation metrics, and guarded candidate learning |
| `seasons.py` | Astronomical season calculation using the configured Home Assistant location |
| `naming.py` | Canonical entity object IDs and meter-name slug generation |
| `registry_cleanup.py` | Expected entity registry IDs and targeted legacy entity-ID migration |
| `frontend/` | Lovelace billing cards |
| `translations/`, `strings.json` | German and English Home Assistant UI strings |

## Authoritative data ownership

Contracts and logical meters remain authoritative in Home Assistant config-entry options during the staged R169 migration. They are additionally projected into dedicated SQLite tables (`vm_contracts`, `vm_meters`) with their config-entry association. Historical billing records, bookings, monthly advance overrides, and physical meter periods use separate SQLite tables (`vm_bookings`, `vm_advance_rates`, `vm_monthly_advances`, `vm_physical_meter_periods`). Migration metadata is stored separately in `vm_migration_state`. The previous `vm_state` JSON snapshot remains a compatibility copy during this stage; all writes synchronize the domain tables in the same SQLite transaction. Foreign keys connect logical meters, bookings, advance rates, and monthly advances to existing contract/meter rows using `ON DELETE SET NULL`; unresolved legacy references remain intact in the JSON payload and are not guessed. This deliberate dual representation is a migration bridge. `_read()` now obtains these record collections from the separated tables, while the snapshot remains available for rollback and portable JSON export. Contracts and logical meters are re-synchronized from all active config entries during setup. The detailed migration behavior and current limitations are documented in `DATENBANK_MIGRATION_R169.md`.

## Entity naming and migration

Canonical entity object IDs are generated centrally by `naming.py`. Balance sensor unique IDs use the role suffixes `verbrauch_kontostand` and `einspeisung_kontostand`; `registry_cleanup.py` must use those exact unique IDs when mapping legacy registry entries to canonical `sensor.verbrauchsmonitor_<meter>_...` entity IDs. Registry updates are restricted to entities owned by this integration config entry. Never remove or rename unrelated entities.

## Monthly advances and balances

Monthly advance overrides are keyed by meter, direction, contract, and calendar month. Each edit is validated before the database transaction. Negative amounts are rejected; zero is valid. Only changed months receive new history versions. An edit must not cascade into later months or alter the recurring contract advance. Aborting the form performs no write. The balance entities are refreshed after a successful save/reload. Actual booking records remain separate from advance configuration/history.

## Forecast and reliability model

Consumption and feed-in use separate forecast sensors and separate persistent learning stores, keyed by logical meter ID and direction. No samples, forecast records, model parameters, or reliability values are shared between meters or directions.

The initial billing-period projection keeps measured energy authoritative and shapes only the remaining period with a local profile. The runtime passes the exact local `as_of` instant and the explicit billing-period end; the remaining fraction of the current day and every day/hour through the final billing day are included without re-counting measured time. DST-aware elapsed seconds are used for time-prorated base-price accrual, and the live balance and forecast share the same pricing helper. Both consumption and feed-in use date, hour, astronomical season, solar elevation/azimuth, calculated local sunrise/sunset, and daylight duration. Consumption uses a bounded low-sun/short-day demand feature; feed-in additionally uses the per-meter set of selected compass directions. A meter may select any combination of north/east/south/west or leave the set empty; new feed-in meters default to south. Multiple selected directions are averaged as an equal-weight directional prior because no per-orientation panel capacities are configured. An empty selection uses a neutral four-direction prior rather than silently assuming south. When sufficient meter history exists, historical monthly rates remain the primary signal and a bounded solar correction refines future days only. Solar calculations run locally from Home Assistant latitude/longitude and the configured timezone; no external weather or solar service is called. Generic profiles are priors, not measured household or PV production data. Metered feed-in is treated as exported energy, not total PV generation.

The hourly learner stores immutable predictions for UTC target-hour boundaries and compares completed intervals with cumulative Recorder statistics. A forecast record is never overwritten when a later cycle creates a new estimate for the same target. Evaluations are idempotently keyed by meter, direction, and target hour. MAE, relative error, signed bias, and measured reliability are calculated from these comparisons. The card may replace the six-hour startup value with measured reliability after five completed hourly comparisons; the background learner retains its stricter 24-comparison threshold for its persisted reliability state. A candidate global scale correction is estimated from the older half of the evaluation history and accepted only when it improves MAE on the untouched newer half; accepted changes increment the model version. Learning history is bounded and persisted in Home Assistant storage, independently for each meter/direction.

Reliability is calculated by the extensible backend registry in `reliability.py`. Module A evaluates consumption/feed-in forecast quality; module B evaluates financial forecast quality. Each contribution supplies a score and an impact weight. The aggregator normalizes only available modules and emits one percentage. Missing history is omitted; completed hourly forecast/actual comparisons contribute to A after the configured minimum sample count. The registry accepts arbitrary future module keys; the architecture is not limited to A/B/C/D. There is no random seed, artificial minimum score, or fixed startup delay.

## Live billing time basis

The elapsed billing-period display is calculated from billing-period start to the exact current local timestamp. Percentages always show two localized decimal places. Whole residual days are shown without decimals; fractional days show two decimal places. The residual-day count starts at the last completed calendar-month anniversary. The current-month cost average uses accrued energy, the continuously accrued base price, and the exact elapsed time since billing start. The date on which a historical baseline was entered is not used as the averaging start.

The accrued annual base price is prorated continuously by elapsed seconds from billing-period start, using the actual length of the current Gregorian year and capped at the annual price. The full contractual annual base price remains a reference value in the UI; the accrued amount is the live value.

Configured instantaneous power entities are shown in the compact row aligned to the right of the elapsed-period percentage/duration subline, with separate German labels for current consumption and current feed-in. The label/value group uses a slightly larger 10px treatment and an 8px internal gap; the Watt value remains right-aligned. The combined progress/power metadata row has one thin divider below it, separating it from the work-price/feed-in-tariff row. The tariff row itself has no thin bottom border because the thicker finance-section divider follows.

## Data-management navigation and release metadata

Data management is a navigation menu with two direct destinations: individual reset scopes and database administration. Database administration is not a reset checkbox and cannot be triggered by the reset form. Destructive resets retain their separate confirmation step. Release version, stage, and revision are maintained as constants and supplied to the About dialog as placeholders.

## Persistence and recovery

The SQLite database is stored at `/config/verbrauchsmonitor.db`; its rolling backup is `/config/verbrauchsmonitor-backup.db`. The legacy JSON source is retained after one-time migration. Database resets must preserve a backup and require explicit confirmation. Config-entry options remain the authoritative store for contracts and meters.

## Verification boundary

Unit and regression tests cover deterministic domain behavior and source-level frontend rules. They do not prove successful startup, reload, Recorder access, registry migration, or visual rendering in a real Home Assistant installation. Those require a live target-system test.

## Forecast entity update performance (R125)

Forecast sensors must not execute projection, history-dependent modelling, or other substantial calculations from the synchronous `native_value` property. The property returns only the last completed cached value. Forecast inputs are snapshotted on the Home Assistant event loop, the pure forecast calculation runs through the executor, and the result plus diagnostic attributes are published together. Refreshes are serialized per forecast entity and are scheduled after source-meter state changes, hourly learning, history reloads, and hourly astronomical season/solar refreshes.

## Billing-card layout refinement (R126)

The forecast box order is season label, reliability, forecast end heading, expected billing balance, and the monthly advance recommendation when the financial rules permit one. The reliability row is directly above the forecast heading. The billing-period progress and current-power metadata share one row; that row has a single thin bottom divider before the tariff row. Current-power text is 10px with a 12px line height and an 8px gap between its left label and right-aligned Watt value. The tariff row remains borderless at the bottom to avoid duplicating the thicker finance-section divider.


## Forecast card and advance recommendation messaging (R127)

The forecast calculation uses the model-projected remaining kWh to calculate the remaining energy value; it must not replace the seasonal/solar/orientation projection with an independent linear cost extrapolation. The expected account balance applies booked and future scheduled advances, additional payments, credits, signed corrections, and one-off extra charges exactly once. Feed-in monthly advance defaults are gross payout amounts, including VAT where configured.

The reliability display is populated from the available A/B module aggregate as soon as forecast inputs are evaluated. If no module has usable evidence, the backend explicitly reports unavailable rather than inventing a percentage. The 15-minute limit is a maximum safeguard for any pending UI state, not a deliberate wait.

The forecast card keeps the season label first, followed by the forecast end-date heading, reliability, expected billing balance, and either a monthly advance recommendation or an explicit explanation. Reliability is rendered directly below the forecast heading; moving it there also removes the former gap above the heading.

Recommendation suppression is a domain decision, not a frontend calculation. The forecast backend supplies a reason code. The card translates these reason codes into German or English explanations: `final_payment_period`, `no_remaining_payment_gap`, and `insufficient_reliability`. A generic localized explanation is used only when a recommendation is unavailable without a more specific reason. The existing safety rule remains: no new monthly recommendation is calculated when fewer than two future payment dates remain.

## Lovelace resource lifecycle and recovery (R130)

The card JavaScript static HTTP route and the Lovelace storage resource are independent registrations. The route is tracked in Home Assistant process-local integration data and is registered once. Registration calls are serialized with a per-instance asynchronous lock so `async_setup`, `async_setup_entry`, reloads, and retry callbacks cannot race to create duplicate routes or resources. If Home Assistant reports that the route already exists, the integration treats that as an already-healthy route and continues with resource registration instead of aborting.

Lovelace resource storage may initialize after the integration. If Lovelace or its resource collection is not ready, one retry is scheduled after 15 seconds; repeated calls share that timer. Successful registration cancels it. In storage mode, the integration finds the resource by its URL without the cache query, updates the existing item in place to the current versioned URL and `module` type, or creates it if absent. YAML resource mode remains manually managed. The version query changes with each release to invalidate stale browser module caches.

## One-time repair of legacy feed-in monthly advances (R131)

R128/R129 could persist the contract-default feed-in payout as a monthly override of `0.00`. R130 correctly treated explicit manual zeros as authoritative, but that also preserved the accidental legacy rows. R131 repairs this narrow historical case when the monthly feed-in editor is opened: for the selected meter and contract, the latest active zero override in each affected month is superseded by the contract's gross monthly payout amount. The previous row remains in the audit history and the replacement records its migration reason and superseded record ID.

The migration is persisted as a per-meter/per-contract marker in the database migration metadata. It is executed at most once, so a zero deliberately entered after R131 remains a valid override. Only feed-in rows belonging to the selected meter and contract are eligible; consumption records, other meters, and nonzero monthly overrides are untouched. Contract amounts are stored net and converted to gross using the contract VAT rate before repair, matching the editor's payout display unit. A legacy feed-in-only contract may use the former generic `monthly_advance` field as a fallback.


## Optionale Umgebungsentitäten (R150; unverändert in R151)

Die Optionen der Prognosekonfiguration können Außentemperatur, Außenhelligkeit, Windrichtung, Tagesniederschlag und Luftfeuchtigkeit referenzieren. Die Prognosesensoren übernehmen diese IDs in ihren lokalen Berechnungskontext. Zustandsänderungen lösen eine Neuberechnung aus; fehlende oder unplausible Werte werden ausgelassen.


## Measurement validation (R169)

`measurement_validation.py` is the shared parser and monotonicity gate for cumulative meter readings. It rejects empty, textual, negative, boolean, NaN, and infinite values. Equal and increasing values are accepted. Decreases are rejected unless the active period contains an explicit meter-change record with a valid old-meter end reading that is consistent with the stored baseline and previous accepted value. The source reading, accepted reference, and period state are not updated for rejected samples. Calendar rollover does not itself authorize a decreasing counter.

## Forecast model 3 – calendar seasons (R169)

`calendar_season_projection()` is an independent third model. It derives daily averages for meteorological seasons from usable per-meter/per-direction history and projects only the remaining days in the billing period. It does not apply the solar profile and does not fill missing seasonal evidence with zero. The existing historical-monthly/seasonal and solar-profile models remain independent. Available model outputs are combined with fixed normalized weights; unavailable models are omitted rather than penalized. Model diagnostics are returned in the forecast result and do not create additional Home Assistant entities.
