Here is a **clean, concise `README.md`** with only the essentials you asked for: folder structure, installation steps, and usage example — **no deep explanations**.

---

# openeo-dedl-plugin

Plugin that adds **Sentinel-3 OLCI `.SEN3` SAFE product support** to the **local backend** of the modified `openeo-python-client`.
Uses **Satpy** to load `.SEN3` data as an openEO `DataCube`.

---

## 📁 Folder Structure

```
openeo-dedl-plugin/
│
├── pyproject.toml
└── src/
    └── openeo_dedl_plugin/
        ├── __init__.py
        ├── sen3.py
        ├── s3_olci_discovery.py
        └── local_loader.py
```

---

## 🔧 Installation (editable mode)

```bash
git clone https://github.com/suriyahgit/openeo-python-client.git
cd openeo-python-client
git checkout dedl_trial
pip install -e .
pip install "gdal==$(gdal-config --version)" openeo-processes-dask[implementations]

git clone https://github.com/suriyahgit/openeo-dedl-plugin
cd openeo-dedl-plugin
pip install -e .
```

---

## 🚀 Usage Example

```python
import openeo
from openeo_dedl_plugin import register_all
import warnings

warnings.filterwarnings("ignore")
warnings.simplefilter(action = "ignore", category = RuntimeWarning)

# Register discovery + data loader handlers
register_all()

# Directory containing .SEN3 SAFE products
con = openeo.local.LocalConnection(
    local_collections_path="/home/sdhinakaran/test_DEDL/data"
)

print(con.list_collections())

# Load a Sentinel-3 OLCI SAFE product
cube = con.load_collection(
    "/home/sdhinakaran/test_DEDL/data/S3B_OL_1_ERR____20240625T083313_20240625T091737_20240921T223114_2664_094_278______MAR_R_NT_004.SEN3",
    fetch_metadata=True,
)

cube # process graph should pop up here
cube.execute()  # data array should pop up
```
With bands filtering!

```python
import openeo
from openeo_dedl_plugin import register_all
import warnings

warnings.filterwarnings("ignore")
warnings.simplefilter(action = "ignore", category = RuntimeWarning)

register_all()

con = openeo.local.LocalConnection(
    local_collections_path="/home/sdhinakaran/test_DEDL/data"
)

print(con.list_collections())

cube = con.load_collection(
    "/home/sdhinakaran/test_DEDL/data/S3B_OL_1_ERR____20240625T083313_20240625T091737_20240921T223114_2664_094_278______MAR_R_NT_004.SEN3",
     bands=["humidity", "total_ozone"], fetch_metadata=True,
)

cube
cube.execute()  # or cube.download_result(...)

```

---
