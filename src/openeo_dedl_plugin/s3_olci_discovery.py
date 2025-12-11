# openeo_dedl_plugin/s3_olci_discovery.py

from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
from datetime import datetime

from openeo.local.collections import register_local_collection_handler
from .sen3 import DEFAULT_OLCI_VARS, olci_metadata_from_safe

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
    Discovery handler for Sentinel-3 OLCI ERR .SEN3 products.
    """
    # Only act on .SEN3 directories
    if not path.is_dir():
        return None
    if not (path.suffix == ".SEN3" or path.name.endswith(".SEN3")):
        return None

    # 1. Derive metadata from Satpy/SEN3 helper
    try:
        meta = olci_metadata_from_safe(path)
        bbox = meta["bbox"]
        temporal_interval = meta["temporal_interval"]
        t_min, t_max = temporal_interval[0]
        bands = meta["bands"]
    except Exception as e:
        _log.warning("Failed to derive OLCI metadata from %s: %s. "
                     "Falling back to global bbox and unknown time.", path, e)
        bbox = [[-180.0, -90.0, 180.0, 90.0]]
        temporal_interval = [[None, None]]
        t_min, t_max = None, None
        bands = list(DEFAULT_OLCI_VARS)

    # 2. Simple platform/product fields from SAFE name
    name = path.name
    if name.endswith(".SEN3"):
        name_wo = name[:-5]
    else:
        name_wo = name
    parts = name_wo.split("_")
    platform_id = parts[0] if len(parts) > 0 else "Sentinel-3"
    instrument = "OLCI"

    level = None
    if len(parts) >= 3:
        level = parts[2]

    if level == "1":
        processing_level = "L1B"
    elif level == "2":
        processing_level = "L2"
    else:
        processing_level = "Unknown"

    providers = [
        {
            "name": "EUMETSAT",
            "roles": ["producer", "licensor"],
            "url": "https://www.eumetsat.int/",
        },
        {
            "name": "European Space Agency (ESA)",
            "roles": ["producer"],
            "url": "https://sentinels.copernicus.eu/",
        },
    ]

    keywords = [
        "Copernicus",
        "Sentinel-3",
        "OLCI",
        "Ocean and Land Colour Instrument",
        "Radiance",
        "L1B",
        "Full Resolution",
        "Ocean colour",
        "Marine",
        "Optical",
    ]

    summaries: Dict[str, Any] = {
        "platform": [platform_id],
        "constellation": ["Sentinel-3"],
        "instruments": [instrument],
        "processing:level": [processing_level],
    }
    product_type = "_".join(parts[1:4]) if len(parts) >= 4 else None

    eo_bands = [{"name": b} for b in bands]
    summaries["eo:bands"] = eo_bands

    title_level = processing_level if processing_level != "Unknown" else "L1/L2"
    title = f"{platform_id} {instrument} {title_level} product ({name})"

    if product_type:
        desc_prod = product_type
    else:
        desc_prod = "OLCI SAFE"

    metadata: Dict[str, Any] = {
        "stac_version": "1.0.0",
        "type": "Collection",
        "id": path.as_posix(),
        "title": title,
        "description": (
            f"Sentinel-3 Ocean and Land Colour Instrument (OLCI) "
            f"{desc_prod} product in SAFE (.SEN3) format, "
            "as provided by EUMETSAT/ESA and exposed via openEO local collections."
        ),
        "license": "Copernicus free and open data licence",
        "providers": providers,
        "links": [],
        "keywords": keywords,
        "extent": {
            "spatial": {"bbox": bbox},
            "temporal": {"interval": temporal_interval},
        },
        "cube:dimensions": {
            "x": {
                "type": "spatial",
                "axis": "x",
                # We only know geographic bbox; exact pixel extents will be in the data,
                # but for metadata this is fine.
                "extent": [bbox[0][0], bbox[0][2]],
                "reference_system": "EPSG:4326",
            },
            "y": {
                "type": "spatial",
                "axis": "y",
                "extent": [bbox[0][1], bbox[0][3]],
                "reference_system": "EPSG:4326",
            },
            "t": {
                "type": "temporal",
                "extent": [t_min, t_max],
            },
            "bands": {
                "type": "bands",
                "values": bands,
            },
        },
        "summaries": summaries,
    }

    return metadata

def register() -> None:
    """
    Register the Sentinel-3 .SEN3 discovery handler into
    openeo.local.collections.
    """
    register_local_collection_handler(sen3_collection_handler)
