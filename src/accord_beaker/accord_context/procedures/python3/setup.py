# Bind the ACCORD stack in the subkernel so the agent and the user start from
# the same namespace.
#
# Every import is individually guarded. deepscale pulls in cartopy and cfgrib,
# rosetta pulls in cdsapi and sheerwater, and a partial install is a normal
# state to be in -- a forecaster who only wants to fetch data should not have
# the notebook fail to start because the plotting stack is absent. Whatever
# does not bind here, the agent can import itself and see the real traceback.

import numpy as np
import xarray as xr

_accord_loaded = []
_accord_missing = {}

try:
    import rosetta

    _accord_loaded.append("rosetta")
except Exception as err:  # noqa: BLE001 - report at startup, never raise
    _accord_missing["rosetta"] = f"{type(err).__name__}: {err}"

try:
    import deepscale as ds

    _accord_loaded.append("deepscale")
except Exception as err:  # noqa: BLE001
    _accord_missing["deepscale"] = f"{type(err).__name__}: {err}"
