# Home Assistant – VerbrauchsMonitor

**Version:** 0.0.2  
**Status:** Public Beta  
**Revision:** R113

VerbrauchsMonitor is a Home Assistant integration for monitoring, analyzing, and calculating energy consumption and energy feed-in.

This version is provided as a public beta. It allows interested users to test the integration under real-world conditions and provide feedback on its functionality and usability.

## Beta Status

This version is still under testing.

- Features may change in future versions.
- Bugs and inconsistencies may occur.
- Results should not be used as the sole basis for billing without independent verification.
- Before installation and updates, create a backup of your Home Assistant configuration and integration data.

## Installation via HACS

1. Open HACS in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add the following repository:

   `https://github.com/Muschelschubser26/HA-Integration-VerbrauchsMonitor-Beta`

5. Select **Integration** as the category.
6. Click **Add**.
7. Search for **VerbrauchsMonitor** and install it.
8. Restart Home Assistant.

## Manual Installation

1. Download the ZIP archive of the desired release.
2. Extract the archive.
3. Copy the `verbrauchsmonitor` folder into:

   `config/custom_components/verbrauchsmonitor/`

4. Restart Home Assistant.
5. Navigate to **Settings → Devices & Services → Add Integration**.
6. Search for **VerbrauchsMonitor** and follow the configuration steps.

## Download

Available beta versions are provided through the GitHub Releases section.

Current version:

`VerbrauchsMonitor 0.0.2 – Beta R113`

## Feedback and Bug Reports

Feedback from beta testers is explicitly welcome.

When reporting an issue, please include:

- Home Assistant version
- VerbrauchsMonitor version and revision
- Affected feature
- Expected behavior
- Actual behavior
- Relevant error messages from the Home Assistant logs

Please do not publish passwords, access tokens, or other personal information.

## Known Limitations

The following items are still open development topics:

- Complete history tracking of physical meter replacements
- Time-proportional calculation of tariff changes within a billing period
- Separate base charge for energy feed-in
- Combined export and import of configuration and local data
- Freely configurable billing sections
- Extended handling and correction of invalid meter reading decreases

These limitations are known and will be considered during further development.

## Versioning

Release archives follow this naming convention:

`Integration-VerbrauchsMonitor-x.y.z-Beta-Rxyz.zip`

Where:

- `x.y.z` represents the product version.
- `Rxyz` represents the Development revision on which the beta is based.

Beta versions retain the exact Development revision number.

## License

VerbrauchsMonitor is released under the MIT License.

Copyright (c) 2026 Muschelschubser26

The complete license terms are provided in the `LICENSE` file.

## Project

VerbrauchsMonitor is independently developed and is not part of the official Home Assistant project.
