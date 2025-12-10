# openeo_dedl_plugin/local_loader.py
from pathlib import Path

import openeo.local.processing as _local_processing
from openeo_pg_parser_networkx.process_registry import Process
import openeo_processes_dask.specs as _specs

from .sen3 import open_olci_wfr_sen3

# Keep reference to the original implementation
_original_load_local_collection = _local_processing.load_local_collection


def _load_collection_with_dedl(*args, **kwargs):
    """
    Wrapper around the original load_local_collection that adds
    support for extra formats (e.g. .SEN3) and then falls back.
    """
    collection_id = kwargs.get("id") or kwargs.get("collection_id")
    if collection_id is None:
        return _original_load_local_collection(*args, **kwargs)

    path = Path(collection_id)

    # 1) New: Sentinel-3 .SEN3 folder
    if path.suffix == ".SEN3" or path.name.endswith(".SEN3"):
        da = open_olci_wfr_sen3(path)
        return da

    # 2) Fallback to the original behaviour (.nc, .zarr, .tif, .tiff, ...)
    return _original_load_local_collection(*args, **kwargs)


def register_dedl_local_plugin():
    """
    Register our wrapper as the implementation of 'load_collection'
    in the local ProcessRegistry.
    """
    _local_processing.PROCESS_REGISTRY["load_collection"] = Process(
        spec=_specs.load_collection,
        implementation=_load_collection_with_dedl,
    )

