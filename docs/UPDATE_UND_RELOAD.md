# Update and Reload Procedure

## Before updating

1. Create a full Home Assistant backup.
2. Keep a copy of the current `custom_components/verbrauchsmonitor/` directory.
3. Do not delete `verbrauchsmonitor.db` or `verbrauchsmonitor-backup.db` during a normal integration update.

## Install Beta R122

1. Extract the archive.
2. Replace `/config/custom_components/verbrauchsmonitor/` with the complete directory from `custom_components/verbrauchsmonitor/` in the archive.
3. Ensure no files from an older version remain in the integration directory.
4. Restart Home Assistant completely.
5. Check **Settings → System → Logs** for integration startup, migration, Recorder, or entity-registry errors.
6. Reload the dashboard/browser to refresh the JavaScript card.

## Entity registry migration

On config-entry setup, the integration computes canonical entity IDs from the configured logical meter names. Only registry entries belonging to the current integration config entry are considered. Balance unique IDs use the role suffixes `verbrauch_kontostand` and `einspeisung_kontostand`. Review the resulting entity IDs and Recorder history after the first startup. Keep the pre-update backup until this check is complete.

## Monthly advance changes

After saving monthly advance overrides, the options flow reloads the config entry. The sensor platform rebuilds its entities from the updated ledger. Confirm the balance state and attributes after the reload. A changed month must not modify another month or the recurring contract advance.

## Rollback

If startup or migration fails, stop Home Assistant, restore the previous integration directory and restore the pre-update Home Assistant backup if data or registry state changed. Do not attempt to repair a partially migrated entity registry by deleting entities manually without a backup.
