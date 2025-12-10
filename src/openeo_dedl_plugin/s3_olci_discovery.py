# openeo_dedl_plugin/s3_olci_discovery.py

from pathlib import Path
from typing import Any, Dict, Optional

from openeo.local.collections import register_local_collection_handler


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

    # NOTE: extent/cube:dimensions are *placeholder* values; you should
    # extract proper bbox/time from the data if needed.
    metadata: Dict[str, Any] = {
        "id": path.as_posix(),
        "title": path.name,
        "description": "Sentinel-3 OLCI WFR product (.SEN3)",
        "stac_version": "1.0.0",
        "extent": {
            "spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]},
            "temporal": {"interval": [[None, None]]},
        },
        "cube:dimensions": {
            "x": {"type": "spatial", "axis": "x"},
            "y": {"type": "spatial", "axis": "y"},
            "t": {"type": "temporal"},
            "bands": {"type": "bands"},
        },
    }

    return metadata


def register() -> None:
    """
    Register the Sentinel-3 .SEN3 discovery handler into
    openeo.local.collections.
    """
    register_local_collection_handler(sen3_collection_handler)
