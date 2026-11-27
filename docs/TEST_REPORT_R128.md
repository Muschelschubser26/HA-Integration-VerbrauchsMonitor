# Test Report – Beta R128

## Scope
Per-meter feed-in orientation selection now accepts multiple directions or no direction. New feed-in meters default to south. Existing scalar and list values are normalized without losing valid stored choices. Feed-in forecast remains available with an empty direction selection and uses a neutral four-direction solar prior. Forecast card wording is neutral and the agreed divider/layout refinements are included.

## Automated checks
- Python compilation: passed.
- JavaScript syntax (`node --check`): passed.
- JSON parsing: all integration JSON files passed.
- German/English translation key parity: 179 keys in each language, no missing keys.
- Unit/regression suite: 426 passed.
- ZIP integrity and archive structure: checked after packaging.

## Runtime limitation
No complete Home Assistant Core instance with the user's Recorder database is available in this build environment. Live config-flow rendering, startup timing, and final browser layout require verification after installation. The native config-flow selector cannot provide a supported two-column layout; multi-select is implemented as a native list.
