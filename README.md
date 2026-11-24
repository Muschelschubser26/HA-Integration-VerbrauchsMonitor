# VerbrauchsMonitor

Home Assistant custom integration for the local management of electricity meters, contracts, tariffs, billing periods, payments, and consumption/feed-in forecasts.

**Project identifier:** `ha-verbrauchsmonitor`  
**Integration domain:** `verbrauchsmonitor`  
**SemVer:** `0.0.2`  
**Package version:** `Beta R115`

German is the default language. The user interface also supports English and follows the language configured in Home Assistant. All processing and storage take place locally in Home Assistant. There is no unsolicited cloud communication or telemetry.

## Features

- Multiple logical electricity meters and multiple contracts within one integration.
- Optional assignment of consumption and feed-in meter readings, as well as optional power and outdoor brightness entities.
- Separate billing directions for electricity consumption and feed-in.
- Contract and tariff management with net/gross inputs, configurable VAT, and separate price types.
- Billing periods, initial meter readings, and history of the origin and changes of initial values.
- Local booking management for monthly instalments, special payments, credits, and corrections.
- Separate account balances for consumption and feed-in.
- Forecasts per source meter and billing direction; seasonal weighting is only used when sufficient Recorder history and data quality are available.
- Dedicated Lovelace billing card with selection of logical meter and billing direction.
- Database status, optimization, import/export, and reset functions through the integration interface.

The availability of individual input fields and displays depends on the configuration. Optional data sources that have not been configured are not replaced with supposedly valid measurement values.

## Requirements

- Home Assistant Core **2026.11.1 or newer** (project target according to `hacs.json`; actual compatibility must be verified in the target installation).
- One or more Home Assistant sensor entities providing meter readings. Power values and outdoor brightness are optional.
- Seasonal forecasts require suitable Recorder long-term statistics or sufficient existing detailed history.

The integration has no additional Python runtime dependencies beyond those provided by the Home Assistant environment (`manifest.json`: `requirements` is empty).

## Installation

### Manual installation

1. Create a Home Assistant backup before updating.
2. Copy the `custom_components/verbrauchsmonitor/` directory from this project to `/config/custom_components/verbrauchsmonitor/`.
3. Completely replace any existing integration directory; do not leave old files in the directory.
4. Fully restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**, search for **VerbrauchsMonitor**, and start the setup.
6. After setup, open the integration options to manage additional contracts, meters, billing periods, bookings, and forecasts.

### Lovelace card

In Lovelace storage mode, the integration registers the card resource automatically. Then reload the dashboard or browser and search for **VerbrauchsMonitor** under **Add Card**.

When using YAML resource mode, the following resource must be added as a module:

`/verbrauchsmonitor/verbrauchsmonitor-card.js`

Each card instance is configured for one logical meter and one billing direction (consumption or feed-in). Additional meters or billing directions require a separate card instance.

## Configuration and operation

Initial setup is performed through the Config Flow. Subsequent changes are made through the integration's Options Flow.

- **Contracts:** Contract name and details, billing period, energy price or feed-in tariff, base price, VAT, and agreed monthly instalments.
- **Meters:** Logical meter name, optional meter number, and source entities for consumption and feed-in.
- **Billing:** Billing start, meter reading baselines, and billing values.
- **Bookings:** Special payments, credits, and corrections assigned to a meter and billing direction.
- **Monthly instalments:** Monthly amounts can be maintained separately for each meter and billing direction.
- **Forecasts:** Consumption and feed-in forecasts can be enabled and assigned separately.
- **Data management:** Database information, optimization, export/import, and reset actions requiring confirmation.

### Monthly instalments and account balance logic

A contractually agreed monthly instalment is automatically treated as paid on the first day of each month within the respective billing period. No manual payment confirmation is required. An explicitly assigned instalment booking replaces the automatic amount for the same month to prevent double counting. Consumption and feed-in instalments are processed separately. Future first days of the month are treated as expected payments in forecasts and do not change the current account balance.

Credits and corrections are stored as separate, traceable bookings. Account balances follow the customer's perspective: negative values represent an amount owed, while positive values represent a credit balance.

## Storage and privacy

The integration configuration is stored in the Home Assistant Config Entry data. Business-related bookings and other persistent integration data are stored locally in SQLite.

The main database is located at `/config/verbrauchsmonitor.db`; the continuously updated single backup database is located at `/config/verbrauchsmonitor-backup.db`.

The previous JSON data store at `.storage/verbrauchsmonitor_data.json` is migrated to SQLite once during the first startup and remains unchanged as a migration source. JSON remains the portable format for data export and import.

The backup is created consistently using the SQLite Backup API. SQLite WAL and transaction mechanisms protect the active data set.

No credentials for external services are required. There is no automatic telemetry and no unsolicited transmission of meter or contract data. Follow the displayed instructions before reset or import operations and create a Home Assistant backup before making major changes.

## Updates and restart

- Changes to Python files, `manifest.json`, or dependencies: fully restart Home Assistant.
- Changes exclusively to the Lovelace JavaScript card: reload the dashboard/browser; update the browser cache if necessary.
- Changes to integration options: saving triggers a Config Entry reload.

A Config Entry reload does not re-import modified Python modules and therefore does not replace a full Home Assistant restart after a code update.

## Documentation and tests

- `docs/ARCHITEKTUR.md`: Components, data flow, and storage responsibilities.
- `docs/INSTALLATION.md`: Installation and operating instructions.
- `docs/UPDATE_UND_RELOAD.md`: Update and reload behavior.
- `docs/ANFORDERUNGEN.md`: Requirements list and implementation status.
- `docs/OFFENE_PUNKTE.md`: Known limitations and required target-system checks.
- `tests/`: Automated unit and regression tests.

Automated tests are part of the development verification process. A successful automated test run does not replace a complete runtime test in a real Home Assistant installation.

## License and contact

The package includes a `LICENSE` file containing the MIT License text. The rights holder must separately confirm the legal authorization of this license before public distribution.

Support: **Support@gehtdoch.eu**
