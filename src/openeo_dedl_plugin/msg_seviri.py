# src/openeo_dedl_plugin/msg_seviri.py
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import xarray as xr
from satpy.scene import Scene

_log = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


DEFAULT_SEVIRI_VARS = [
    "HRV",
    "IR_016",
    "IR_039",
    "IR_087",
    "IR_097",
    "IR_108",
    "IR_120",
    "IR_134",
    "VIS006",
    "VIS008",
    "WV_062",
    "WV_073",
]

SEVIRI_3KM_VARS = [
    "IR_016",
    "IR_039",
    "IR_087",
    "IR_097",
    "IR_108",
    "IR_120",
    "IR_134",
    "VIS006",
    "VIS008",
    "WV_062",
    "WV_073",
]

SEVIRI_HRV_VARS = ["HRV"]


def _validate_seviri_band_selection(requested: Sequence[str]) -> None:
    s = set(requested)
    allowed = set(DEFAULT_SEVIRI_VARS)
    unknown = sorted(s - allowed)
    if unknown:
        raise ValueError(f"Unknown SEVIRI bands requested: {unknown}. Allowed: {DEFAULT_SEVIRI_VARS}")

    has_hrv = "HRV" in s
    has_3km = any(b in s for b in SEVIRI_3KM_VARS)

    if has_hrv and has_3km:
        raise ValueError(
            "SEVIRI band selection mixes incompatible grids: HRV (high-resolution) "
            "cannot be combined with the 3km channels in a single openEO cube. "
            "Load HRV alone (bands=['HRV']) OR load only 3km channels "
            f"(bands={SEVIRI_3KM_VARS})."
        )


def open_seviri_nat(path: Path, variables: Optional[Sequence[str]] = None) -> xr.DataArray:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path!s} does not exist.")
    if path.is_dir():
        raise ValueError(f"{path!s} is a directory; expected a .nat file.")

    scn = Scene(reader="seviri_l1b_native", filenames=[str(path)])

    # DEFAULT POLICY (Option 1):
    # - default load: only 3km channels (exclude HRV) to keep one consistent grid
    # - if user selects bands: validate they are from ONE group (HRV-only or 3km-only)
    if variables is None or list(variables) == []:
        load_vars = list(SEVIRI_3KM_VARS)
    else:
        load_vars = list(variables)

    _validate_seviri_band_selection(load_vars)

    scn.load(load_vars)

    start_time = getattr(scn, "start_time", None)
    end_time = getattr(scn, "end_time", None)
    if start_time and end_time:
        acq_time = start_time + (end_time - start_time) / 2
    else:
        acq_time = start_time or end_time

    ds: xr.Dataset = scn.to_xarray()

    # enforce stable ordering + only requested vars
    ordered = [b for b in load_vars if b in ds.data_vars]
    ds = ds[ordered]

    if acq_time is not None:
        ds = ds.expand_dims(time=[acq_time])
    else:
        ds = ds.expand_dims(time=[np.datetime64("NaT")])

    da = ds.to_array(dim="bands").transpose("time", "bands", "y", "x")
    return da


def seviri_metadata_from_nat(path: Path) -> Dict[str, Any]:
    scn = Scene(reader="seviri_l1b_native", filenames=[str(path)])
    start_time = getattr(scn, "start_time", None)
    end_time = getattr(scn, "end_time", None)

    def _to_iso(dt):
        if dt is None:
            return None
        s = dt.replace(microsecond=0).isoformat()
        return s.replace("+00:00", "Z")

    t_min = _to_iso(start_time)
    t_max = _to_iso(end_time)

    return {
        "t_min": t_min,
        "t_max": t_max,
        "temporal_interval": [[t_min, t_max]],
        "bbox": [[-180.0, -90.0, 180.0, 90.0]],  # refine later if you want
        "bands": list(DEFAULT_SEVIRI_VARS),
    }

