# openeo_dedl_plugin/__init__.py
from .local_loader import register_dedl_local_plugin
from .s3_olci_discovery import register as register_sen3_discovery


def register_all() -> None:
    """
    Register all plugin hooks:

    * discovery:   .SEN3 directories show up in LocalConnection.list_collections()
    * I/O loader:  load_collection() can open .SEN3 directories as a DataCube
    """
    register_dedl_local_plugin()
    register_sen3_discovery()