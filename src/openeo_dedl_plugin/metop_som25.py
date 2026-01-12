# src/openeo_dedl_plugin/metop_somo25.py
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import xarray as xr

_log = logging.getLogger(__name__)

try:
    from ascat.eumetsat.level2 import AscatL2File
except Exception as e:
    raise ImportError(
        "Missing dependency 'ascat'. Install it to read METOP ASCAT SOMO25 products."
    ) from e


DEFAULT_SOMO25_VARS: List[str] = [
    # Core soil moisture variables
    "sm",
    "sm_noise",
    "sm_mean",
    "sm_sens",
    # Backscatter / model vars commonly useful
    "sig40",
    "sig40_noise",
    "slope40",
    "slope40_noise",
    "dry_sig40",
    "wet_sig40",
    # Flags / probabilities / ancillary
    "snow_prob",
    "frozen_prob",
    "wetland",
    "topo",
    "proc_flag",
    "agg_flag",
    "corr_flag",
]


def _resolve_nat(path: Path) -> Optional[Tuple[Path, Path]]:
    """
    Resolve (collection_id_path, nat_file_path).

    Supports:
      - collection_id is a .nat file
      - collection_id is a directory containing exactly one .nat file
    """
    if path.is_file() and path.suffix.lower() == ".nat":
        return path, path

    if path.is_dir():
        nats = sorted(path.glob("*.nat"))
        if len(nats) == 1:
            return path, nats[0]
    return None


def _to_iso(dt) -> Optional[str]:
    if dt is None:
        return None
    # dt may be numpy datetime64 already in some cases
    try:
        if isinstance(dt, np.datetime64):
            if np.isnat(dt):
                return None
            # convert to seconds precision ISO
            s = np.datetime_as_string(dt, unit="s")
            return s.replace(" ", "T") + "Z"
        s = dt.replace(microsecond=0).isoformat()
        return s.replace("+00:00", "Z")
    except Exception:
        return None


def _grid_swath_to_line_node(ds: xr.Dataset) -> xr.Dataset:
    """
    Convert 1D obs stream into 2D swath grid using (line_num, node_num) -> (y, x).
    Keeps lat/lon as 2D coordinates.
    """
    if "line_num" not in ds or "node_num" not in ds:
        raise ValueError("ASCAT dataset missing line_num/node_num; cannot grid to swath.")

    line = ds["line_num"].values
    node = ds["node_num"].values

    # They are floats in your sample; round to nearest integer
    if np.issubdtype(line.dtype, np.floating):
        line = np.rint(line).astype(np.int32)
    else:
        line = line.astype(np.int32)

    if np.issubdtype(node.dtype, np.floating):
        node = np.rint(node).astype(np.int32)
    else:
        node = node.astype(np.int32)

    ds2 = ds.assign_coords(y=("obs", line), x=("obs", node))
    ds2 = ds2.set_index(obs=("y", "x")).unstack("obs")

    # ensure lat/lon are 2D coords (they become data vars or coords depending on xarray)
    if "lat" in ds2:
        ds2 = ds2.set_coords("lat")
    if "lon" in ds2:
        ds2 = ds2.set_coords("lon")

    return ds2


def open_somo25_nat(path: Path, variables: Optional[Sequence[str]] = None) -> xr.DataArray:
    """
    Open METOP ASCAT SOMO25 (.nat) using ascat library.

    Returns openEO-friendly DataArray with dims: (time, bands, y, x)
    where (y,x) is the native swath grid (line,node).
    """
    path = Path(path)
    resolved = _resolve_nat(path)
    if not resolved:
        raise ValueError(f"{path!s} is neither a .nat file nor a directory with exactly one .nat file.")
    _, nat_path = resolved

    ds, _md = AscatL2File(nat_path).read(generic=True, to_xarray=True)

    # band selection
    if variables is None or list(variables) == []:
        load_vars = list(DEFAULT_SOMO25_VARS)
    else:
        load_vars = list(variables)

    unknown = sorted(set(load_vars) - set(ds.data_vars))
    if unknown:
        raise ValueError(f"Unknown SOMO25 variables requested: {unknown}. Available: {sorted(ds.data_vars)}")

    # keep only requested variables + geolocation/time support
    keep = set(load_vars)
    for v in ("lat", "lon", "time", "line_num", "node_num"):
        if v in ds:
            keep.add(v)
    ds = ds[list(keep.intersection(set(ds.variables)))]

    # grid to (y,x)
    ds2 = _grid_swath_to_line_node(ds)

    # pick a single acquisition time per file (midpoint), like your SEVIRI implementation
    tmin = ds["time"].min().values if "time" in ds else np.datetime64("NaT")
    tmax = ds["time"].max().values if "time" in ds else np.datetime64("NaT")
    if isinstance(tmin, np.datetime64) and isinstance(tmax, np.datetime64) and not np.isnat(tmin) and not np.isnat(tmax):
        acq_time = tmin + (tmax - tmin) / 2
    else:
        acq_time = tmin if not np.isnat(tmin) else tmax

    ds2 = ds2[load_vars]  # only requested variables become bands
    ds2 = ds2.expand_dims(time=[acq_time])

    da = ds2.to_array(dim="bands").transpose("time", "bands", "y", "x")
    return da


def somo25_metadata_from_nat(path: Path) -> Dict[str, Any]:
    """
    Minimal discovery metadata (bbox, temporal interval, bands).
    """
    path = Path(path)
    resolved = _resolve_nat(path)
    if not resolved:
        raise ValueError(f"{path!s} is neither a .nat file nor a directory with exactly one .nat file.")
    _, nat_path = resolved

    ds, _md = AscatL2File(nat_path).read(generic=True, to_xarray=True)

    tmin = _to_iso(ds["time"].min().values) if "time" in ds else None
    tmax = _to_iso(ds["time"].max().values) if "time" in ds else None

    bbox = [[-180.0, -90.0, 180.0, 90.0]]
    if "lon" in ds and "lat" in ds:
        lon = ds["lon"].values
        lat = ds["lat"].values
        bbox = [[
            float(np.nanmin(lon)), float(np.nanmin(lat)),
            float(np.nanmax(lon)), float(np.nanmax(lat)),
        ]]

    return {
        "t_min": tmin,
        "t_max": tmax,
        "temporal_interval": [[tmin, tmax]],
        "bbox": bbox,
        "bands": list(DEFAULT_SOMO25_VARS),
    }
