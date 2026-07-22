# Report what the ACCORD stack looks like in this subkernel, for the preview
# panel. Returns a plain JSON-serializable dict as the cell's value.
#
# The credential block is the point of this procedure. rosetta reaches
# Copernicus, ECMWF and IRI, each with its own dotfile, and a missing one
# surfaces as a 403 partway through a slow request. Showing presence up front
# turns that into something the forecaster can fix before starting.


def _accord_environment():
    from importlib.metadata import PackageNotFoundError, version
    from pathlib import Path

    packages = {}
    for dist, module in (("accord-rosetta", "rosetta"), ("accord-deepscale", "deepscale")):
        try:
            packages[module] = version(dist)
        except PackageNotFoundError:
            packages[module] = "not installed"

    # Presence only -- never read or display the contents of a credential file.
    credentials = {
        "~/.cdsapirc": "Copernicus CDS: c3s/* products and obs/era5*",
        "~/.ecmwfapirc": "ECMWF MARS: S2S reforecast fallback",
        "~/.pycpt_dlauth": "IRI Data Library: c3s/ecmwf-seas51c",
    }
    credential_status = {
        path: {"present": Path(path).expanduser().is_file(), "used_for": purpose}
        for path, purpose in credentials.items()
    }

    imported = sorted(set(globals().get("_accord_loaded", [])))
    failed = dict(globals().get("_accord_missing", {}))

    environment = {
        "packages": packages,
        "imported_in_subkernel": imported,
        "credentials": credential_status,
    }
    if failed:
        environment["import_errors"] = failed
    return environment


_accord_environment()
