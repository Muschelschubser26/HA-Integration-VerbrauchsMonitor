# Test Report – VerbrauchsMonitor Beta R130

## Scope

Correction and hardening of Lovelace custom-card delivery and registration after R129 dashboards reported `Custom element doesn't exist: verbrauchsmonitor-billing-card`.

## Root cause

The frontend registration function registered the HTTP static path and returned immediately on *any* exception. The integration calls card registration from both `async_setup` and `async_setup_entry`. Home Assistant rejects registering the same static path twice. The second call therefore returned before it could inspect or repair the Lovelace resource. In addition, the initial setup could run before Lovelace's resource storage collection was available, and there was no delayed retry. This left the JS file present in the integration package but the browser resource absent, so the custom element was never defined.

## Changes

- Static-path registration is now tracked per Home Assistant process and performed once.
- A duplicate-route response is treated as an already-served route, not as a fatal registration failure.
- Static-path failures no longer prevent an independent attempt to register the Lovelace resource when the route is already present.
- If Lovelace or its resource collection is not initialized yet, one retry is scheduled after 15 seconds. Repeated setup calls do not create parallel retry timers.
- A successful registration cancels the pending retry.
- YAML resource mode remains user-managed and does not create a storage resource.
- Existing card resources are updated in place to the current versioned URL and module type; a second resource is not created.
- Both custom card definitions are asserted to remain in the packaged JavaScript file.
- The frontend resource cache-busting identifier is advanced to `0.0.2-beta-r130`.

## Automated tests

Dedicated behavior tests cover:

1. Initial setup before Lovelace initialization followed by a successful second setup call.
2. Delayed retry after Lovelace becomes available.
3. Updating an existing outdated resource without duplication.
4. YAML resource mode.
5. Presence of both custom card definitions in the packaged asset.

## Final validation results

- Full automated suite: **445 passed**.
- Python compilation (`compileall`): passed.
- JavaScript syntax (`node --check`): passed.
- JSON validation: **5 files valid**.
- German/English translation parity: **179 / 179 keys**, no missing keys.
- Dedicated frontend registration behavior tests: **7 passed**.
- ZIP archive integrity and complete project structure: verified after packaging.

A live Home Assistant startup, actual Lovelace storage backend, and browser custom-element rendering test are not available in this build environment. This remains explicitly outstanding; the automated behavior tests exercise the registration timing, duplicate-route, retry, version-update, and concurrency cases using Home Assistant API doubles.
