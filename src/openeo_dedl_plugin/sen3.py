# openeo_dedl_plugin/sen3.py
from pathlib import Path
from typing import Dict, Any, Optional, List, Sequence
import logging
import warnings
import numpy as np

import xarray as xr
from satpy import find_files_and_readers
from satpy.scene import Scene
from xcube_resampling.rectify import rectify_dataset

_log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=RuntimeWarning)


# Default set of bands & auxiliary variables to load
DEFAULT_OLCI_VARS: List[str] = [
    # Core OLCI bands
    "Oa01", "Oa02", "Oa03", "Oa04", "Oa05",
    "Oa06", "Oa07", "Oa08", "Oa09", "Oa10",
    "Oa11", "Oa12", "Oa13", "Oa14", "Oa15",
    "Oa16", "Oa17", "Oa18", "Oa19", "Oa20", "Oa21",

    # Geometry
    "solar_zenith_angle",
    "solar_azimuth_angle",
    "satellite_zenith_angle",
    "satellite_azimuth_angle",

    # Flags & masks
    "quality_flags",
    "mask",

    # Auxiliary variables (from your new list)
    "altitude",
    "humidity",
    "latitude",
    "longitude",
    "sea_level_pressure",
    "total_columnar_water_vapour",
    "total_ozone",
]



def open_olci_err_sen3(
    path: Path,
    variables: Optional[Sequence[str]] = None,
) -> xr.DataArray:
    """
    Open a Sentinel-3 OLCI L1B ERR SAFE product (.SEN3) using Satpy
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

    #ds = rectify_dataset(ds, interp_methods="nearest")

    # 4. Add time dimension (length 1)
    ds = ds.expand_dims(time=[acq_time])

    # 5. Collapse all data variables into "bands" → one DataArray
    da = ds.to_array(dim="bands")
    da = da.transpose("time", "bands", "y", "x")

    return da

def olci_err_metadata_from_safe(path: Path) -> Dict[str, Any]:
    """
    Derive basic metadata (time interval, bbox, band names) for a
    Sentinel-3 OLCI L1B ERR SAFE product.

    This is intentionally lighter than full radiance loading:
    we only load longitude/latitude to get the spatial footprint.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"{path!s} does not exist.")
    if not path.is_dir():
        raise ValueError(f"{path!s} is not a directory. Expected a .SEN3 SAFE folder.")

    # IMPORTANT: same base_dir logic as open_olci_err_sen3
    base_dir = path.parent

    files = find_files_and_readers(
        sensor="olci",
        base_dir=str(base_dir),
        reader="olci_l1b",
    )

    if not files:
        raise ValueError(f"No supported files found under {base_dir!s} for reader 'olci_l1b'.")

    scn = Scene(filenames=files)

    # Temporal info: start/end time from Scene
    start_time = getattr(scn, "start_time", None)
    end_time = getattr(scn, "end_time", None)

    def _to_iso(dt) -> Optional[str]:
        if dt is None:
            return None
        s = dt.replace(microsecond=0).isoformat()
        return s.replace("+00:00", "Z")

    t_min = _to_iso(start_time)
    t_max = _to_iso(end_time)

    # Spatial info: load longitude/latitude only, get bbox
    bbox = [[-180.0, -90.0, 180.0, 90.0]]  # fallback
    try:
        scn.load(["longitude", "latitude"])
        ds = scn.to_xarray()

        if "longitude" in ds and "latitude" in ds:
            lon = ds["longitude"].values
            lat = ds["latitude"].values

            min_lon = float(np.nanmin(lon))
            max_lon = float(np.nanmax(lon))
            min_lat = float(np.nanmin(lat))
            max_lat = float(np.nanmax(lat))

            bbox = [[min_lon, min_lat, max_lon, max_lat]]
        else:
            _log.warning("longitude/latitude not found in Scene xarray; using global bbox.")
    except Exception as e:
        _log.warning("Failed to derive bbox from Scene: %s. Using global bbox.", e)

    # Band names: use the same list as the data loader
    bands = list(DEFAULT_OLCI_VARS)

    return {
        "t_min": t_min,
        "t_max": t_max,
        "temporal_interval": [[t_min, t_max]],
        "bbox": bbox,
        "bands": bands,
    }