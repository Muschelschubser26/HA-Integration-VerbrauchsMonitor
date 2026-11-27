# Requirements and Verification Register

This document tracks the project's agreed requirements. A requirement is not considered complete merely because a related UI element exists. Runtime-only checks must be marked as requiring target Home Assistant verification.

## Core requirements

| Area | Requirement | Verification status |
|---|---|---|
| Contracts/meters | Multiple contracts and logical meters; stable IDs; optional meter number and source entities | Implemented in config-entry options; verify multi-meter runtime |
| Accounting | Consumption and feed-in remain separate | Covered by domain and regression tests; target-system verification remains |
| Tariffs | Net/gross, configurable VAT including 0%, work price, base price, feed-in remuneration | Domain tests; historical tariff validity remains a known project gap |
| Monthly advances | Per-meter, per-direction, per-month overrides; zero valid; negative invalid; no automatic propagation | Unit/regression coverage; live form/reload verification remains |
| History | Previous monthly override versions retained; unchanged values do not create versions | Regression coverage |
| Payments | Advances, additional payments, credits, and corrections remain distinct | Existing ledger tests; verify imported legacy data in target system |
| Balances | Recalculate from the correct costs, revenues, and allocated bookings | Domain tests; verify immediate sensor refresh in target system |
| Database | SQLite integrity, backup, optimize, import/export, confirmed reset | Unit tests; real HA filesystem/runtime verification remains |
| Entity naming | Central canonical IDs; migration only for this integration's registry entries | Mapping tests; real registry migration must be tested in HA |
| Forecast | Initial local profile forecast without requiring 12 months of own history; separate consumption/feed-in models; astronomical season, solar position, calculated sunrise/sunset, daylight duration for both directions, selected feed-in directions, and history-based seasonal learning | Forecast-model tests; Recorder and location behavior require target-system validation |
| Reliability | Extensible A/B reliability modules; one displayed percentage; missing history omitted; no artificial floor or random initialization; further modules register dynamically | Unit tests for six-hour expiry, measured comparisons, and evidence fallback; Recorder runtime validation remains |
| Dashboard | Mark initial reliability distinctly; allow provisional recommendations only when at least two future payment dates remain and a positive payment gap remains after booked/scheduled payments | Source-level frontend tests; visual HA test remains |
| Localization | German fallback and English UI; matching translation keys | JSON/key-parity tests |
| Documentation | English README and technical guides | Updated for this package |

## Known limitations requiring explicit runtime or future work

- A full Home Assistant startup/reload/unload cycle has not been executed in this isolated test environment.
- Recorder long-term statistics and detail-history availability depend on the user's HA database and retention settings.
- Entity-registry migration must be validated against a real pre-update registry backup before production use.
- Responsive card rendering and selector layout require browser testing in Home Assistant.
- Historical tariff validity snapshots and immutable end-of-period billing snapshots remain separate project requirements and are not claimed as implemented by this package.


## R119 additions

- Monthly advance corrections remain individually editable by month, reject negative values, accept zero, retain audit history, and reload balance entities after saving without changing the recurring contract advance.
- Billing elapsed time and accrued annual base price use the current local timestamp rather than whole-month rounding.
- Current consumption/feed-in power is displayed below the respective reading when configured.
- Data management offers separate direct navigation to reset scopes and database administration.
- Release metadata is centralized and exposed in the About dialog as version, stage, and revision placeholders.
- Fixed numeric reference scenario asserts expected forecast amounts and account balance to the cent.
- Compass-direction selection field identifiers are no longer UUID-based and old meter-editor compass field is removed; legacy values are used as a fallback during reconfiguration. The two-column visual layout of native Home Assistant selector controls still requires a live UI-specific implementation/verification.


## R124 additions

- Solar geometry now affects both consumption and feed-in future profiles. The consumption prior uses a bounded daylight/solar-elevation feature; feed-in additionally uses all selected compass directions. History-based projections retain historical monthly rates as the dominant signal and apply only a bounded correction to future days.
- Local sunrise and sunset are calculated from Home Assistant coordinates, date, and configured timezone. No external solar/weather service is used.
- Monthly advance recommendations are suppressed when fewer than two future payment dates remain or no positive payment gap remains after actual bookings and future scheduled payments. The former 70% floor is removed because it could contradict credits or scheduled payments.
- Current power is aligned to the right of the compact period-progress subline for both directions. The thin divider below current power is removed.
- The season label is shown above the forecast heading; expected balance and reliability follow the heading without a redundant divider.
- The two-column compass selector remains a known UI limitation pending a custom config-flow frontend.

## R125 performance requirement

- Forecast entity `native_value` access must remain constant-time and must never run forecast calculations synchronously. Expensive projection work runs in the executor from an asynchronously refreshed, serialized cache.


## R126 additions

- Forecast-card order: season, reliability, forecast end heading, expected billing balance, and a monthly recommendation only when payment-date and positive-payment-gap rules permit it.
- Current consumption/feed-in power shares the progress metadata row, uses 10px text with an 8px label/value gap, and keeps the Watt value right-aligned.
- Exactly one thin divider separates the progress/current-power metadata row from the tariff row. The tariff row has no bottom divider where the thicker finance-section divider follows.
- Automated source-level tests cover the approved ordering, spacing, and divider placement. Live Home Assistant browser verification remains required.


## R127 additions

- Forecast card order is season, forecast heading, reliability, expected billing balance, then monthly advance recommendation or a reason-specific explanation.
- Reliability must appear immediately below the forecast heading. A and B are internal modules aggregated into one percentage. Missing measurement history is omitted; no random initial value or artificial floor is allowed. Further modules can be registered dynamically.
- Suppressed recommendations must not leave an unexplained blank area; the UI explains final-payment-period protection, a fully covered forecast amount, or insufficient measured reliability.
- Final-payment-period protection diagnostics must reflect the active `months_remaining < 2` rule.


## R128 – Himmelsrichtungen je Einspeisungszähler
- Die Himmelsrichtung wird ausschließlich am jeweiligen Einspeisungszähler konfiguriert, nicht global im Prognosedialog.
- Mehrfachauswahl von Norden, Osten, Süden und Westen ist zulässig; eine leere Auswahl ist ebenfalls zulässig.
- Neue Einspeisungszähler erhalten standardmäßig Süden.
- Bestehende Einzel- und Mehrfachauswahlen werden migrationssicher in die per-Zähler-Liste überführt.
- Ohne Auswahl bleibt die Einspeisungsprognose verfügbar und verwendet ein neutrales Vier-Richtungen-Profil. Mehrfachauswahlen werden mangels Flächen-/Leistungsgewichtung gleichgewichtet kombiniert.
- Die zweispaltige Darstellung der nativen Home-Assistant-Formularauswahl bleibt offen.
