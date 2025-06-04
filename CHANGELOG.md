# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Guiding Principles:
* Changelogs are for humans, not machines.
* There should be an entry for every single version.
* The same types of changes should be grouped.
* Versions and sections should be linkable.
* The latest version comes first.
* The release date of each version is displayed.
* Mention whether you follow Semantic Versioning.

Types of changes:
Added - for new features
Changed - for changes in existing functionality
Deprecated - for soon-to-be removed features
Removed - for now removed features
Fixed - for any bug fixes
Security - in case of vulnerabilities
-->

## [1.7.0] - 2025-03-11

### Security

- Updated image dependencies for security updates
- Updated Dockerfiles to install python packages via virtual environment due to image update

## [1.6.0] - 2024-08-23

### Added

- Added support for XD224 Paradise. The mockup is not included.

## [1.5.3] - 2023-11-02

### Added

- BootOrder key to Intel mockup

## [1.5.2] - 2023-10/30

### Added

- Added an Antero mockup

## [1.5.1] - 2023-08-17

### Added

- Added an Open BMC mockup

## [1.5.0] - 2023-04-19
### Fixed
- Fixed delete for redfish subscriptions

## [1.4.0] - 2023-03-20

### Added
- Add support retrieving credentials from Vault when running within as a pod in CSM. When `AUTH_CONFIG` is set to
  `from_vault`. 

    When RIE starts up it will check Vault at `secret/hms-creds/${BMC_XNAME}`, and if no value exists there then will 
    fallback to the default  password source. On CSM systems there are two sources of default BMC credentials one for 
    Mountain `secrets/meds-cred/global/ipmi` and one for River `secrets/reds-creds/global/default`.
- Add a SLS loader script that to load SLS hardware objects into SLS.

### Changed
- Seed the random number generator based off the BMC's xname. This allows for RIE to generate the same serial numbers,
  and MAC addresses if it restarts. 

### Fixed
- Properly randomize GPU serial numbers
- Only apply the Mountain MAC schema to the BMC/Manager BMC MAC addresses. The NMN node MAC addresses are not algorithmic.

## [1.3.1] - 2022-07-07

### Fixed

- Randomize power supply serial numbers if present.

## [1.3.0] - 2022-07-01

### Fixed

- CASMHMS-5604: Fixed an issue where node MAC addresses where node being randomized.

### Changed

- Remove build dependencies at the end of the build step to create a leaner docker image. The image size is now 156MB, when in the pervious release is 1.42GB.

## [1.2.0] - 2022-06-17

### Added

- Added mockup for XL675d with A100 GPUs

### Fixed

- Static resource path handling now normalizes paths

## [1.1.0] - 2022-04-21

### Added

- Dynamic resources for the CertificateService allowing for performing ReplaceCertificate actions.
- Dynamic resources for Manager Network Protocol allowing for editing values.
- Dynamic resources for the Managers allowing for performing Manager.Reset actions.
- Dynamic resources for the Chassis allowing for performing Chassis.Reset actions.
- Added mockups for CMM, Gigabyte compute, Intel compute, and Slingshot_Switch_Blade.

## [1.0.0] - 2022-04-15

### Added

- Dynamic resources for the AccountService allowing for adding/removing/editing authorization accounts.
- Dynamic resources for the SessionService allowing for token authorization.
- Added a default loader that attempts to apply known dynamic resources to a mockup depending on URIs available in the static mockup.
- Added mockups for EX420, EX425, EX235n, DL325, and XL675d_A40
- Added docker-compose that stands up a CSM environment and loads HSM with references to the emulator.
- Github workflow for building and releasing the image.

### Changed

- Bard Peak references have been replaced with EX235a.
- Refactored files and directories so all required emulator code is source controlled in this repo.
- Refactored how loaders work. All <BMC_type>_loader.py files will create subclasses of the Loader class in loader.py.
- The generic loader (loader.py) handles generically applying dynamic resources to Mockups. This makes it no longer required to create a <BMC_type>_loader.py per emulated type unless further customizations are needed.

## [0.2.0] - 2022-03-24

### Added

- Support for Deep PATCH for Olympus power limiting.
- Support for changing the 'ControlMode' field for Olympus power controls.
- Dynamic resources for the EventService allowing for subscribing to redfish events.
- Support for sending redfish events when compute system PowerState is affected.

### Changed

- Responses from dynamic resources are now all valid json.

## [0.1.0] - 2022-03-18

### Added

- This is the initial release.
- Supports Bard Peak emulation with dynamic resources for Power Capping, System ResetActions, and Firmware Update.
