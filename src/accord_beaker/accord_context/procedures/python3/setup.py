# Bind the ACCORD stack in the subkernel so the agent and the user start from
# the same namespace.
#
# Every import is individually guarded. africas2s pulls in cartopy and cfgrib,
# acmaddl pulls in cdsapi and sheerwater, and a partial install is a normal
# state to be in -- a forecaster who only wants to fetch data should not have
# the notebook fail to start because the plotting stack is absent. Whatever
# does not bind here, the agent can import itself and see the real traceback.

import numpy as np
import xarray as xr

_accord_loaded = []
_accord_missing = {}

try:
    import acmaddl

    _accord_loaded.append("acmaddl")
except Exception as err:  # noqa: BLE001 - report at startup, never raise
    _accord_missing["acmaddl"] = f"{type(err).__name__}: {err}"

try:
    import africas2s as ds

    _accord_loaded.append("africas2s")
except Exception as err:  # noqa: BLE001
    _accord_missing["africas2s"] = f"{type(err).__name__}: {err}"
