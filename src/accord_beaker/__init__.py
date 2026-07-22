# SPDX-FileCopyrightText: 2026-present accord-research
#
# SPDX-License-Identifier: MIT
"""Beaker context for ACCORD seasonal climate forecasting."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("accord-beaker")
except PackageNotFoundError:  # running from a source tree with no install
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
