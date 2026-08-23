# Contributing

Thanks for taking the time to contribute! This document explains how to set up a
development environment, propose changes, and add support for more Edge
drivers.

## Getting Started

1. Fork the repository and clone your fork.
2. Install dependencies (runtime + dev tools):

   ```bash
   make install
   ```

3. Copy the driver you want to patch into `auto_patch/` if you intend to test
   against a new device locally.

## Development Workflow

- **Linting:** `make lint` (`ruff check .`)
- **Formatting:** `make format`, and `make format-check` to verify
- **Tests:** `make test`
- **Schema validation:** `make validate`

`make check` runs all four, which is exactly what CI enforces. Please make sure
it passes before opening a pull request.

CI additionally runs the suite on Python 3.11 and 3.12, lints
`auto_patch/auto_patch.sh` with shellcheck, and verifies the built wheel
installs into a clean environment.

## Adding Support for a New Driver

1. Place a copy of the official SmartThings Edge driver inside `auto_patch/`.
2. Create or update the subdriver template:
   - Add a folder under `auto_patch/subdrivers/` that mirrors how the driver
     handles the desired attributes.
   - Make sure the template exposes `PATCHED_DEVICE_MODELS`.
3. Update the capability mapping in `auto_patch/custom_capability_list.config`.
4. Update `auto_patch/driver2patch.config` with the new driver, handler filename,
   and subdriver folder name.
5. If the driver needs a brand-new handler, add a Lua file under
   `auto_patch/cap-patches/`.
6. Add tests that exercise the new driver, ideally by creating a lightweight
   fixture under `tests/fixtures/`.

## Pull Requests

When submitting a PR:

- Fill out the PR template.
- Reference related issues.
- Describe user impact and testing steps.
- Keep changes focused; prefer multiple smaller PRs to a single large one.

## Reporting Issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`. Include OS details,
Python version, driver name, and full command output whenever possible.

## Code of Conduct

By participating in this project you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
