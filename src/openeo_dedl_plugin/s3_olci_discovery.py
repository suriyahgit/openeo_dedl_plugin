# openeo_dedl_plugin/s3_olci_discovery.py

from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
from datetime import datetime

from openeo.local.collections import register_local_collection_handler
from .sen3 import DEFAULT_OLCI_VARS

_log = logging.getLogger(__name__)


def _parse_safe_times(path: Path) -> List[List[Optional[str]]]:
    """
    Parse start/end time from a Sentinel-3 SAFE product name.

    Example filename:
    S3B_OL_1_ERR____20240625T083313_20240625T091737_20240921T223114_2664_094_278______MAR_R_NT_004.SEN3
                                 ^ start_time         ^ end_time

    Returns a STAC-style temporal interval: [[start_iso, end_iso]].
    If parsing fails, returns [[None, None]].
    """
    name = path.name  # just the last component
    # Strip .SEN3 if present
    if name.endswith(".SEN3"):
        name = name[:-5]

    parts = name.split("_")
    if len(parts) < 5:
        _log.warning("Could not parse times from SAFE name %s", path)
        return [[None, None]]

    start_str = parts[3]  # e.g. 20240625T083313
    end_str = parts[4]    # e.g. 20240625T091737

    def _to_iso(s: str) -> Optional[str]:
        try:
            dt = datetime.strptime(s, "%Y%m%dT%H%M%S")
            # Return RFC3339-ish string with Z
            return dt.replace(microsecond=0).isoformat() + "Z"
        except Exception:
            return None

    start_iso = _to_iso(start_str)
    end_iso = _to_iso(end_str)

    return [[start_iso, end_iso]]


def sen3_collection_handler(path: Path) -> Optional[Dict[str, Any]]:
    """
    Discovery handler for Sentinel-3 OLCI WFR .SEN3 products.

    Called by openeo.local.collections._get_local_collections for every
    path in the search tree (except for known .nc/.zarr/.tif/.tiff files).

    If this handler recognizes the path as a .SEN3 directory, it returns
    a STAC-like collection metadata dictionary; otherwise it returns None.
    """
    # Only act on .SEN3 directories
    if not path.is_dir():
        return None

    if not (path.suffix == ".SEN3" or path.name.endswith(".SEN3")):
        return None

    # Temporal extent from SAFE product name
    temporal_interval = _parse_safe_times(path)

    # Spatial extent: for now, global bbox; we can refine later
    bbox = [[-180.0, -90.0, 180.0, 90.0]]

    metadata: Dict[str, Any] = {
        "id": path.as_posix(),
        "title": path.name,
        "description": "Sentinel-3 OLCI WFR product (.SEN3)",
        "stac_version": "1.0.0",
        "extent": {
            "spatial": {"bbox": bbox},
            "temporal": {"interval": temporal_interval},
        },
        "cube:dimensions": {
            "x": {"type": "spatial", "axis": "x"},
            "y": {"type": "spatial", "axis": "y"},
            "t": {"type": "temporal"},
            "bands": {
                "type": "bands",
                # Important so CollectionMetadata doesn't warn "No band names".
                "values": list(DEFAULT_OLCI_VARS),
            },
        },
        # You can later add "summaries" and "eo:bands" here if you want
        # richer metadata (wavelengths, common names, etc.).
    }

    return metadata


def register() -> None:
    """
    Register the Sentinel-3 .SEN3 discovery handler into
    openeo.local.collections.
    """
    register_local_collection_handler(sen3_collection_handler)
