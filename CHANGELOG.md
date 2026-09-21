# Changelog

All notable milestones for this project are documented here.
This project is tagged at each milestone (see `git tag` / GitHub Releases).

## [v1.0.0] - Final release
- First tagged, stable release of the Brewery Simulator.
- 500+ I/O tags across 8 ISA-88/95 plant areas, published via MQTT5.
- HTTP control API (FastAPI) for live speed/pause/fault control.
- Full documentation (README, ARCHITECTURE, UDT specs).

## [v0.9.0] - Testing complete
- Added a pytest unit-test suite for the pure-logic core: `physics.py`,
  `fault_codes.py`, and `tag_store.py`.
- 54 tests passing; 100% coverage on `physics.py` and `fault_codes.py`,
  92% on `tag_store.py`.
- Merged via pull request from `feature/unit-tests` into `main`.

## [v0.2.0] - Sensor/switch improvements
- Improved sensor and switch simulation accuracy.

## [v0.1.0] - Initial development
- First working version of the simulation engine, tag store, and MQTT
  publisher.
