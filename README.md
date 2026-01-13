---

# openeo-dedl-plugin

An **openEO local backend plugin** developed in the context of **Destination Earth (DEDL)** that enables **native EUMETSAT EO products** to be discovered and loaded as **openEO DataCubes** using the modified `openeo-python-client`.

The plugin bridges **native EO formats** (SAFE / EPS Native) to **xarray-based openEO workflows**, leveraging **Satpy** and **ascat** under the hood.

---

## ✨ Key Features

* 📦 **Native EO format support** (`.SEN3`, `.nat`)
* 🔍 **Automatic discovery** as openEO STAC-like collections
* 🧊 **Lazy, xarray-backed DataCubes**
* 🧩 **Band filtering** via `load_collection(bands=[...])`
* 🏠 Works with **openEO local backend** (no server required)

---

## 🛰️ Currently Supported Products

1. **Sentinel-3 OLCI**

   * L1B ERR (`.SEN3`)
   * L2 WFR (`.SEN3`)
2. **MSG SEVIRI**

   * High Rate SEVIRI Level-1.5 Image Data (0°)
   * Native EPS format (`.nat`)
3. **Metop ASCAT**

   * Soil Moisture at 25 km Swath Grid (SOMO25)
   * Near-Real-Time (NRT), native EPS format (`.nat`)

---

## 📁 Folder Structure

```
openeo-dedl-plugin/
│
├── pyproject.toml
├── README.md
├── env_installation_insula.sh
├── .pre-commit-config.yaml
│
└── src/
    └── openeo_dedl_plugin/
        ├── __init__.py
        │
        ├── local_loader.py
        │   # Registers data-level loaders for:
        │   # - Sentinel-3 OLCI (.SEN3)
        │   # - MSG SEVIRI (.nat)
        │   # - Metop ASCAT SOMO25 (.nat)
        │
        ├── sen3.py
        │   # Sentinel-3 OLCI reader (L1B + L2) via Satpy
        │
        ├── s3_olci_discovery.py
        │   # Discovery (STAC Collection) handler for .SEN3 products
        │
        ├── msg_seviri.py
        │   # MSG SEVIRI L1b native (.nat) reader via Satpy
        │
        ├── msg_seviri_discovery.py
        │   # Discovery handler for MSG SEVIRI products
        │
        ├── metop_somo25.py
        │   # Metop ASCAT SOMO25 (.nat) reader via ascat
        │
        └── metop_somo25_discovery.py
            # Discovery handler for Metop ASCAT SOMO25
```

---

## 🔧 Installation (editable mode)

### 1️⃣ Install the modified openEO Python client

```bash
git clone https://github.com/suriyahgit/openeo-python-client.git
cd openeo-python-client
git checkout dedl_trial
pip install -e .
pip install "gdal==$(gdal-config --version)" openeo-processes-dask[implementations]
```

### 2️⃣ Install this plugin

```bash
git clone https://github.com/suriyahgit/openeo-dedl-plugin
cd openeo-dedl-plugin
pip install -e .
```

> 💡 On Insula / Destination Earth JupyterHub, use
> `env_installation_insula.sh` for a fully automated setup.

---

## 🚀 Usage Examples

### Register the plugin

```python
import warnings
import openeo
from openeo_dedl_plugin import register_all

warnings.filterwarnings("ignore")
warnings.simplefilter("ignore", RuntimeWarning)

# Register discovery + data loaders
register_all()
```

---

### 📡 Sentinel-3 OLCI L1B ERR

```python
con = openeo.local.LocalConnection(
    local_collections_path="/home/sdhinakaran/test_DEDL/data"
)

print(con.list_collections())

cube = con.load_collection(
    "/home/sdhinakaran/test_DEDL/data/"
    "S3B_OL_1_ERR____20240625T083313_20240625T091737_20240921T223114_2664_094_278______MAR_R_NT_004.SEN3",
    fetch_metadata=True,
)

cube
cube.execute()
```

#### Band filtering

```python
cube = con.load_collection(
    "/home/sdhinakaran/test_DEDL/data/"
    "S3B_OL_1_ERR____20240625T083313_20240625T091737_20240921T223114_2664_094_278______MAR_R_NT_004.SEN3",
    bands=["humidity", "total_ozone"],
    fetch_metadata=True,
)

cube.execute()
```

---

### 🌊 Sentinel-3 OLCI L2 WFR

```python
cube = con.load_collection(
    "/home/sdhinakaran/test_DEDL/data/"
    "S3B_OL_2_WFR____20240625T084330_20240625T084630_20240626T162746_0179_094_278_1800_MAR_O_NT_003.SEN3",
    bands=["chl_nn", "iop_nn"],
    fetch_metadata=True,
)

cube.execute()
```

---

## 🧠 Design Notes

* **Discovery handlers** expose native products as openEO collections
* **Data loaders** convert native EO formats to:

  ```
  (time, bands, y, x)
  ```
* Grid incompatibilities (e.g. SEVIRI HRV vs 3 km channels) are **explicitly validated**
* The plugin is designed to be **extendable** (MTG-FCI, EPS-SG, etc.)

---