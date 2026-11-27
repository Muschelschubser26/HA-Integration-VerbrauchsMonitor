# Beta R125 Test Report

## Automated validation

- Unit and regression tests: **413 passed**.
- Python compilation: passed for all integration Python modules.
- JavaScript syntax: passed with `node --check`.
- JSON syntax: passed for all JSON files.
- German and English translation key parity: passed by the project test suite.
- Fixed numeric reference scenarios from R124 remain covered and passed.

## Slow entity-update warning analysis

The reported Home Assistant warnings identified two forecast entities whose synchronous `native_value` reads were doing the full forecast calculation. That calculation includes history-based projection and solar-aware model work. R125 changes the lifecycle: `native_value` now returns only `_cached_native_value`; the forecast calculation is prepared from a state/configuration snapshot and executed through `hass.async_add_executor_job`. The refresh is serialized per entity and scheduled after source state changes, hourly learning, history refresh, and hourly season/solar refresh. The resulting state and attributes are written after the asynchronous refresh completes.

## Regression coverage

- `native_value` contains only the cached-value return.
- Forecast calculation is delegated to the executor using `functools.partial`.
- Source-change and season callbacks schedule an asynchronous refresh and state write.
- Cache initialization and per-entity refresh serialization are present.
- Existing fixed-reference forecast, recommendation, solar, payment, billing, and localization tests remain passing.

## Runtime verification boundary

No live Home Assistant instance with the user's Recorder database was available. Consequently, the absence of the warning must be confirmed in the target installation after R125 is installed. The synchronous heavy-calculation path responsible for the warning has, however, been removed from entity state updates. Executor load and actual wall-clock timing with the user's history volume cannot be measured in this environment.
