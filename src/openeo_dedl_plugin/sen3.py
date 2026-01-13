# openeo_dedl_plugin/sen3.py
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import xarray as xr
from satpy import find_files_and_readers
from satpy.scene import Scene
from xcube_resampling.rectify import rectify_dataset

_log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=RuntimeWarning)

# L1B defaults (your current set, adjust if needed)
DEFAULT_OLCI_L1B_VARS: List[str] = [
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

    # Aux vars (keep/adjust as you like)
    "altitude",
    "humidity",
    "latitude",
    "longitude",
    "sea_level_pressure",
    "total_columnar_water_vapour",
    "total_ozone",
]

# L2 defaults (from your list)
DEFAULT_OLCI_L2_VARS: List[str] = [
    "chl_nn",
    "chl_oc4me",
    "iop_nn",
    "iwv",
    "iwv_unc",
    "latitude",
    "longitude",
    "mask",
    "satellite_azimuth_angle",
    "satellite_zenith_angle",
    "solar_azimuth_angle",
    "solar_zenith_angle",
    "trsp",
    "tsm_nn",
    "w_aer",
    "wqsf",
]

# Fallback "union" if we can't determine level
DEFAULT_OLCI_VARS: List[str] = sorted(
    list(set(DEFAULT_OLCI_L1B_VARS + DEFAULT_OLCI_L2_VARS))
)

def _infer_olci_level_and_reader(path: Path) -> (str, List[str]):
    """
    Inspect SAFE name and decide if it's L1B (ERR, etc.) or L2 (WFR, etc.)
    and return (reader_name, default_var_list).
    """
    name = path.name
    if name.endswith(".SEN3"):
        name = name[:-5]
    parts = name.split("_")

    # very simple heuristic: S3B_OL_1_ERR.... or S3B_OL_2_WFR....
    level = None
    if len(parts) >= 3:
        level = parts[2]

    if level == "1":
        return "olci_l1b", DEFAULT_OLCI_L1B_VARS
    elif level == "2":
        return "olci_l2", DEFAULT_OLCI_L2_VARS

    # Fallback: assume L1B and generic defaults
    _log.warning("Could not infer OLCI level from SAFE name %s, assuming L1B.", path)
    return "olci_l1b", DEFAULT_OLCI_VARS


def open_olci_sen3(
    path: Path,
    variables: Optional[Sequence[str]] = None,
) -> xr.DataArray:
    """
    Open a Sentinel-3 OLCI SAFE product (.SEN3) using Satpy
    and convert it to an xarray.DataArray suitable for openEO local processing.

    Supports both:
      * Level-1B (OL_1_ERR) via reader 'olci_l1b'
      * Level-2  (OL_2_WFR, etc.) via reader 'olci_l2'
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"{path!s} does not exist.")
    if not path.is_dir():
        raise ValueError(f"{path!s} is not a directory. Expected a .SEN3 SAFE folder.")

    base_dir = path.parent

    reader_name, default_vars = _infer_olci_level_and_reader(path)

    files = find_files_and_readers(
        sensor="olci",
        base_dir=str(base_dir),
        reader=reader_name,
    )
    if not files:
        raise ValueError(
            f"No supported files found under {base_dir!s} "
            f"for reader '{reader_name}'."
        )

    scn = Scene(filenames=files)

    # Select variables
    if variables is None:
        load_vars: Sequence[str] = default_vars
    else:
        load_vars = list(variables)

    scn.load(load_vars)

    acq_time = scn.start_time + (scn.end_time - scn.start_time) / 2
    ds: xr.Dataset = scn.to_xarray()

    # ds = rectify_dataset(ds, interp_methods="nearest")  # optional

    ds = ds.expand_dims(time=[acq_time])
    da = ds.to_array(dim="bands").transpose("time", "bands", "y", "x")

    return da


def olci_metadata_from_safe(path: Path) -> Dict[str, Any]:
    """
    Derive basic metadata (time interval, bbox, band names) for a
    Sentinel-3 OLCI SAFE product (L1B or L2).
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"{path!s} does not exist.")
    if not path.is_dir():
        raise ValueError(f"{path!s} is not a directory. Expected a .SEN3 SAFE folder.")

    base_dir = path.parent

    reader_name, default_vars = _infer_olci_level_and_reader(path)

    files = find_files_and_readers(
        sensor="olci",
        base_dir=str(base_dir),
        reader=reader_name,
    )
    if not files:
        raise ValueError(
            f"No supported files found under {base_dir!s} "
            f"for reader '{reader_name}'."
        )

    scn = Scene(filenames=files)

    # Temporal info
    start_time = getattr(scn, "start_time", None)
    end_time = getattr(scn, "end_time", None)

    def _to_iso(dt) -> Optional[str]:
        if dt is None:
            return None
        s = dt.replace(microsecond=0).isoformat()
        return s.replace("+00:00", "Z")

    t_min = _to_iso(start_time)
    t_max = _to_iso(end_time)

    # Spatial info via lat/lon
    bbox = [[-180.0, -90.0, 180.0, 90.0]]
    try:
        scn.load(["longitude", "latitude"])
        ds = scn.to_xarray()
        if "longitude" in ds and "latitude" in ds:
            lon = ds["longitude"].values
            lat = ds["latitude"].values
            bbox = [[
                float(np.nanmin(lon)), float(np.nanmin(lat)),
                float(np.nanmax(lon)), float(np.nanmax(lat)),
            ]]
        else:
            _log.warning("longitude/latitude not found in Scene xarray; using global bbox.")
    except Exception as e:
        _log.warning("Failed to derive bbox from Scene: %s. Using global bbox.", e)

    bands = list(default_vars)

    return {
        "t_min": t_min,
        "t_max": t_max,
        "temporal_interval": [[t_min, t_max]],
        "bbox": bbox,
        "bands": bands,
    }
