# Installation and Update Guide — VerbrauchsMonitor 0.0.1

## Requirements

- Home Assistant Core 2026.11.1 or later.
- At least one valid Home Assistant source sensor for a cumulative meter reading.
- Recorder history or long-term statistics for historical forecast evaluation.

## Installation through HACS

1. Open HACS and select **Integrations**.
2. Open **Custom repositories** from the menu.
3. Add `https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor` as an **Integration** repository.
4. Find **VerbrauchsMonitor** and install it.
5. Restart Home Assistant completely.
6. Add the integration under **Settings → Devices & services → Add integration** and complete the configuration.

## Manual installation

1. Create a full Home Assistant backup.
2. Copy the complete `custom_components/verbrauchsmonitor/` directory from the archive to `/config/custom_components/verbrauchsmonitor/`. Replace the old directory completely; do not merge files.
3. Restart Home Assistant completely.
4. Add or configure VerbrauchsMonitor under **Settings → Devices & services**.
5. Refresh the dashboard/browser after startup.

## Lovelace resource

In storage mode, the integration registers its card resource automatically. Registration is idempotent and retries while Lovelace storage initializes. After an upgrade, the resource URL is updated with the current integration version.

In YAML resource mode, add `/verbrauchsmonitor/verbrauchsmonitor-card.js` as a JavaScript module. Use one billing-card instance per logical meter and accounting direction.

## Monthly advance editing

Select the meter and accounting direction before opening the month list. The current month is excluded. The list starts with the next eligible month and contains at most seven eligible months. The selection can cross a calendar-year boundary.

Each month is independently editable. Negative values are rejected; zero is allowed. Saving unchanged values creates no new history versions. Changing a month does not automatically alter the recurring contract advance or other months. The saved amount applies through the end of the billing period that contains the selected month. After a successful save, the integration reloads its entities so balances are recalculated from the updated ledger.

## Forecast and reliability display

Consumption and feed-in forecast paths are evaluated separately for each logical meter and direction. Forecast inputs include available historical energy data and the configured seasonal/time-of-day/solar context.

The reliability percentage is shown only when the required evidence is available. The current implementation evaluates usable Recorder history using its duration, coverage, continuity, plausibility and forecast method. A usable basis requires at least 12 months of history, at least two samples and at least 50% coverage. The score has no artificial minimum. If the evidence is insufficient, no percentage is fabricated.

Historical forecast-to-actual learning and financial forecast calibration remain subject to the limitations documented in `ZUVERLAESSIGKEIT.md` and `OFFENE_PUNKTE.md`. Recorder availability and quality therefore affect the result.

## Database operations

The database status combines config-entry contract/meter counts with SQLite ledger counts. Before import, reset, or destructive data management, create a Home Assistant backup. Reset operations require explicit confirmation.

## Update and restart behavior

- Replace the integration directory completely.
- Restart Home Assistant after Python, manifest, translation or service-definition changes.
- Refresh the dashboard/browser after frontend-only changes.
- Options-flow changes trigger the integration config-entry reload.

## Test boundary

Automated tests do not replace a live Home Assistant runtime test. Verify startup, reload/unload, Recorder data, entity-registry migrations, config-flow controls, dashboard layout, and real sensor values in the target installation. The release archive documents outstanding runtime checks in `OFFENE_PUNKTE.md`.
