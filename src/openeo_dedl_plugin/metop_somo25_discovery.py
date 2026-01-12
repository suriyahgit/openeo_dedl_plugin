# src/openeo_dedl_plugin/metop_somo25_discovery.py
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from openeo.local.collections import register_local_collection_handler

from .metop_somo25 import DEFAULT_SOMO25_VARS, somo25_metadata_from_nat

_log = logging.getLogger(__name__)


def _resolve_nat(path: Path) -> Optional[Tuple[Path, Path]]:
    if path.is_file() and path.suffix.lower() == ".nat":
        return path, path
    if path.is_dir():
        nats = sorted(path.glob("*.nat"))
        if len(nats) == 1:
            return path, nats[0]
    return None


def metop_somo25_collection_handler(path: Path) -> Optional[Dict[str, Any]]:
    resolved = _resolve_nat(path)
    if not resolved:
        return None

    collection_id_path, nat_path = resolved

    try:
        meta = somo25_metadata_from_nat(nat_path)
        bbox = meta["bbox"]
        temporal_interval = meta["temporal_interval"]
        t_min, t_max = temporal_interval[0]
        bands = meta["bands"]
    except Exception as e:
        _log.warning("Failed to derive SOMO25 metadata from %s: %s", nat_path, e)
        bbox = [[-180.0, -90.0, 180.0, 90.0]]
        temporal_interval = [[None, None]]
        t_min, t_max = None, None
        bands = list(DEFAULT_SOMO25_VARS)

    providers = [
        {"name": "EUMETSAT", "roles": ["producer", "licensor"], "url": "https://www.eumetsat.int/"},
    ]

    return {
        "stac_version": "1.0.0",
        "type": "Collection",
        "id": collection_id_path.as_posix(),
        "title": f"Metop ASCAT Soil Moisture 25 km (SOMO25) ({collection_id_path.name})",
        "description": "Metop ASCAT Soil Moisture 25 km (SOMO25) Level-2 product in EPS native (.nat) format exposed via openEO local collections.",
        "license": "proprietary",
        "providers": providers,
        "links": [],
        "keywords": ["EUMETSAT", "Metop", "ASCAT", "Soil Moisture", "SOMO25", "L2", "Native"],
        "extent": {"spatial": {"bbox": bbox}, "temporal": {"interval": temporal_interval}},
        "cube:dimensions": {
            "x": {"type": "spatial", "axis": "x", "extent": [bbox[0][0], bbox[0][2]], "reference_system": "EPSG:4326"},
            "y": {"type": "spatial", "axis": "y", "extent": [bbox[0][1], bbox[0][3]], "reference_system": "EPSG:4326"},
            "t": {"type": "temporal", "extent": [t_min, t_max]},
            "bands": {"type": "bands", "values": bands},
        },
        "summaries": {"eo:bands": [{"name": b} for b in bands]},
    }


def register() -> None:
    register_local_collection_handler(metop_somo25_collection_handler)
