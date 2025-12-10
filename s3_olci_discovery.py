# openeo_dedl_plugin/s3_olci_discovery.py
from pathlib import Path
from typing import Optional, Dict, Any

from openeo.local.collections import register_local_collection_handler

def sen3_collection_handler(path: Path) -> Optional[Dict[str, Any]]:
    # Only act on .SEN3 directories
    if not path.is_dir() or not (path.suffix == ".SEN3" or path.name.endswith(".SEN3")):
        return None

    # Build minimal STAC-like metadata for LocalConnection.list_collections()
    # In real code you’d inspect one NetCDF inside to derive bbox/time.
    return {
        "id": path.as_posix(),
        "title": path.name,
        "description": "Sentinel-3 OLCI WFR product (.SEN3)",
        "stac_version": "1.0.0",
        "extent": {
            # Fill properly from data; placeholder example:
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "cube:dimensions": {
            "x": {"type": "spatial", "axis": "x"},
            "y": {"type": "spatial", "axis": "y"},
            "t": {"type": "temporal"},
            "bands": {"type": "bands"},
        },
    }

def register():
    register_local_collection_handler(sen3_collection_handler)

