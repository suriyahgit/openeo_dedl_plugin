# openeo_dedl_plugin/__init__.py
from .local_loader import register_dedl_local_plugin
from .discovery import register_dedl_discovery_plugin

def register_all():
    register_dedl_local_plugin()
    register_dedl_discovery_plugin()

