# openeo_dedl_plugin/local_loader.py

from pathlib import Path
from typing import Any, Dict, Optional

import xarray as xr
from openeo.local.processing import register_local_collection_handler

from .sen3 import open_olci_sen3


def _sen3_data_handler(path: Path, args: Dict[str, Any]) -> Optional[xr.DataArray]:
    """
    Data-level handler for Sentinel-3 OLCI .SEN3 directories.

    Supports both Level-1B (e.g. OL_1_ERR) and Level-2 (e.g. OL_2_WFR)
    products via Satpy readers 'olci_l1b' and 'olci_l2'.

    Parameters
    ----------
    path:
        Path to the collection id, as a filesystem path.
    args:
        Full argument dict passed to the 'load_collection' process
        (e.g. includes 'id', 'spatial_extent', 'temporal_extent', 'bands', ...).

    Returns
    -------
    xarray.DataArray or None
        If the path is a .SEN3 directory, returns an array for openEO to use.
        Otherwise returns None to delegate to the default loader.
    """
    # Only handle .SEN3 directories here
    if not path.is_dir():
        return None

    if not (path.suffix == ".SEN3" or path.name.endswith(".SEN3")):
        return None

    # Optionally honour 'bands' selection from the load_collection arguments
    bands_arg = args.get("bands")
    if bands_arg is None or bands_arg in ([], ()):
        variables = None
    else:
        # Expect a list of band names matching OLCI variables
        variables = list(bands_arg)

    da = open_olci_sen3(path=path, variables=variables)
    return da


def register_dedl_local_plugin() -> None:
    """
    Register the .SEN3 data handler with the local 'load_collection' plugin hook.
    """
    register_local_collection_handler(_sen3_data_handler)
