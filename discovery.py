# openeo_dedl_plugin/discovery.py
from pathlib import Path
import logging

import openeo.local.collections as _local_collections

from .sen3 import open_olci_wfr_sen3   # or a lighter metadata-only reader

_log = logging.getLogger(__name__)

_original_get_local_collections = _local_collections._get_local_collections


def _get_local_collections_with_sen3(local_collections_path):
    base = _original_get_local_collections(local_collections_path)
    collections = base["collections"]

    # Make sure we normalize path list like the original
    if isinstance(local_collections_path, str):
        paths = [local_collections_path]
    else:
        paths = list(local_collections_path)

    for root in paths:
        for sen3 in Path(root).rglob("*.SEN3"):
            try:
                # Very lightweight metadata derivation:
                #   - maybe open only geo_coordinates + one band
                #   - or read pre-computed YAML/JSON sidecars
                # Here, just use a stub:
                metadata = {
                    "id": sen3.as_posix(),
                    "title": sen3.name,
                    "description": "Sentinel-3 OLCI WFR product",
                    "stac_version": "1.0.0",
                    "extent": {...},           # fill like _get_netcdf_zarr_metadata
                    "cube:dimensions": {...},  # x,y,t,bands
                }
                collections.append(metadata)
            except Exception as e:
                _log.error(f"Error building metadata for {sen3}: {e}")

    return {"collections": collections}


def register_dedl_discovery_plugin():
    _local_collections._get_local_collections = _get_local_collections_with_sen3

