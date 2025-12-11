# openeo_dedl_plugin/sen3.py

from pathlib import Path
from typing import List, Optional, Sequence

import warnings

import xarray as xr
from satpy import find_files_and_readers
from satpy.scene import Scene

warnings.filterwarnings("ignore", category=RuntimeWarning)

# Default set of bands & auxiliary variables to load
DEFAULT_OLCI_VARS: List[str] = [
    "Oa01", "Oa02", "Oa03", "Oa04", "Oa05",
    "Oa06", "Oa07", "Oa08", "Oa09", "Oa10",
    "Oa11", "Oa12", "Oa13", "Oa14", "Oa15",
    "Oa16", "Oa17", "Oa18", "Oa19", "Oa20", "Oa21",
    "solar_zenith_angle", "solar_azimuth_angle",
    "satellite_zenith_angle", "satellite_azimuth_angle",
    "quality_flags", "mask",
]


def open_olci_wfr_sen3(
    path: Path,
    variables: Optional[Sequence[str]] = None,
) -> xr.DataArray:
    """
    Open a Sentinel-3 OLCI L1B WFR SAFE product (.SEN3) using Satpy
    and convert it to an xarray.DataArray suitable for openEO local processing.

    Parameters
    ----------
    path:
        Path to the .SEN3 directory (SAFE product root).
    variables:
        Optional sequence of variable names to load. If None, a default list
        of OLCI bands + angles + flags is used (DEFAULT_OLCI_VARS).

    Returns
    -------
    xarray.DataArray
        DataArray with dimensions roughly: ('time', 'bands', 'y', 'x').
        Band names are stored in the 'bands' coordinate.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"{path!s} does not exist.")

    if not path.is_dir():
        raise ValueError(f"{path!s} is not a directory. Expected a .SEN3 SAFE folder.")

    # IMPORTANT: Satpy works when base_dir is the parent directory,
    # matching your working snippet.
    base_dir = path.parent

    files = find_files_and_readers(
        sensor="olci",
        base_dir=str(base_dir),
        reader="olci_l1b",
    )

    if not files:
        raise ValueError(f"No supported files found under {base_dir!s} for reader 'olci_l1b'.")

    # Create the Satpy Scene
    scn = Scene(filenames=files)

    # Select variables
    if variables is None:
        load_vars: Sequence[str] = DEFAULT_OLCI_VARS
    else:
        load_vars = list(variables)

    # 1. Load variables (lazy)
    scn.load(load_vars)

    # 2. Acquisition time: mid-point between start and end
    acq_time = scn.start_time + (scn.end_time - scn.start_time) / 2

    # 3. Scene → xarray.Dataset
    ds: xr.Dataset = scn.to_xarray()

    # 4. Add time dimension (length 1)
    ds = ds.expand_dims(time=[acq_time])

    # 5. Collapse all data variables into "bands" → one DataArray
    da = ds.to_array(dim="bands")
    da = da.transpose("time", "bands", "y", "x")

    return da
