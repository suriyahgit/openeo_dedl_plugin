# src/openeo_dedl_plugin/msg_seviri_discovery.py
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from openeo.local.collections import register_local_collection_handler
from .msg_seviri import seviri_metadata_from_nat

_log = logging.getLogger(__name__)

def msg_seviri_collection_handler(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    if path.suffix.lower() != ".nat":
        return None

    try:
        meta = seviri_metadata_from_nat(path)
        bbox = meta["bbox"]
        temporal_interval = meta["temporal_interval"]
        t_min, t_max = temporal_interval[0]
        bands = meta["bands"]
    except Exception as e:
        _log.warning("Failed to derive SEVIRI metadata from %s: %s", path, e)
        bbox = [[-180.0, -90.0, 180.0, 90.0]]
        temporal_interval = [[None, None]]
        t_min, t_max = None, None
        bands = []

    providers = [
        {"name": "EUMETSAT", "roles": ["producer", "licensor"], "url": "https://www.eumetsat.int/"},
    ]

    metadata: Dict[str, Any] = {
        "stac_version": "1.0.0",
        "type": "Collection",
        "id": path.as_posix(),  # consistent with your SEN3 approach :contentReference[oaicite:7]{index=7}
        "title": f"MSG SEVIRI L1b Native ({path.name})",
        "description": "Meteosat SEVIRI Level-1b data in native (.nat) format exposed via openEO local collections.",
        "license": "proprietary",  # adjust if you want; depends on your distribution context
        "providers": providers,
        "links": [],
        "keywords": ["EUMETSAT", "Meteosat", "MSG", "SEVIRI", "L1b", "Native"],
        "extent": {
            "spatial": {"bbox": bbox},
            "temporal": {"interval": temporal_interval},
        },
        "cube:dimensions": {
            "x": {"type": "spatial", "axis": "x", "extent": [bbox[0][0], bbox[0][2]], "reference_system": "EPSG:4326"},
            "y": {"type": "spatial", "axis": "y", "extent": [bbox[0][1], bbox[0][3]], "reference_system": "EPSG:4326"},
            "t": {"type": "temporal", "extent": [t_min, t_max]},
            "bands": {"type": "bands", "values": bands},
        },
        "summaries": {"eo:bands": [{"name": b} for b in DEFAULT_SEVIRI_VARS]},
    }
    return metadata

def register() -> None:
    register_local_collection_handler(msg_seviri_collection_handler)
