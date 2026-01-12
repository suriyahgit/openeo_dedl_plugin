# src/openeo_dedl_plugin/msg_seviri_discovery.py
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from openeo.local.collections import register_local_collection_handler

from .msg_seviri import DEFAULT_SEVIRI_VARS, seviri_metadata_from_nat

_log = logging.getLogger(__name__)


def _is_seviri_nat(p: Path) -> bool:
    name = p.name
    return (
        p.suffix.lower() == ".nat"
        and ("MSG" in name or "SEVI" in name)   # keep it simple
        and "ASCA_SMO" not in name              # explicit exclude
    )

def _resolve_nat(path: Path) -> Optional[Tuple[Path, Path]]:
    if path.is_file() and _is_seviri_nat(path):
        return path, path
    if path.is_dir():
        nats = sorted([p for p in path.glob("*.nat") if _is_seviri_nat(p)])
        if len(nats) == 1:
            return path, nats[0]
    return None


def msg_seviri_collection_handler(path: Path) -> Optional[Dict[str, Any]]:
    resolved = _resolve_nat(path)
    if not resolved:
        return None

    collection_id_path, nat_path = resolved

    try:
        meta = seviri_metadata_from_nat(nat_path)
        bbox = meta["bbox"]
        temporal_interval = meta["temporal_interval"]
        t_min, t_max = temporal_interval[0]
        bands = meta["bands"]
    except Exception as e:
        _log.warning("Failed to derive SEVIRI metadata from %s: %s", nat_path, e)
        bbox = [[-180.0, -90.0, 180.0, 90.0]]
        temporal_interval = [[None, None]]
        t_min, t_max = None, None
        bands = list(DEFAULT_SEVIRI_VARS)

    providers = [
        {"name": "EUMETSAT", "roles": ["producer", "licensor"], "url": "https://www.eumetsat.int/"},
    ]

    return {
        "stac_version": "1.0.0",
        "type": "Collection",
        # IMPORTANT: id must match what user passes to load_collection()
        "id": collection_id_path.as_posix(),
        "title": f"MSG SEVIRI L1b Native ({collection_id_path.name})",
        "description": "Meteosat SEVIRI Level-1b data in native (.nat) format exposed via openEO local collections.",
        "license": "proprietary",
        "providers": providers,
        "links": [],
        "keywords": ["EUMETSAT", "Meteosat", "MSG", "SEVIRI", "L1b", "Native"],
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
    register_local_collection_handler(msg_seviri_collection_handler)
