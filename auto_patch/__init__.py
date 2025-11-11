"""
Helper package for patching SmartThings Edge drivers.

This file exists to make the `auto_patch` directory importable for tests and
potential packaging without changing the existing layout of the project.
"""

from . import patch_handlers, patch_profiles, patch_subdriver  # noqa: F401

__all__ = [
    "patch_profiles",
    "patch_handlers",
    "patch_subdriver",
]
