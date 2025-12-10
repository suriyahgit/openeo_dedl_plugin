# openeo_dedl_plugin/sen3.py
from pathlib import Path
import xarray as xr

def open_olci_wfr_sen3(path: Path) -> xr.DataArray:
    """
    Open a Sentinel-3 OLCI WFR .SEN3 directory as an xarray.DataArray
    with a 'bands' dimension compatible with local openEO processing.
    """
    path = Path(path)

    # Example: load all reflectance sub-datasets and merge
    # Adapt glob pattern according to real filenames
    nc_files = sorted(path.glob("Oa*_radiance.nc"))
    if not nc_files:
        raise IOError(f"No OLCI radiance files found in {path}")

    ds = xr.open_mfdataset([f.as_posix() for f in nc_files],
                           combine="by_coords", parallel=True)

    # Select / rename variables -> construct band stack
    # This is schematic, adapt to your actual var names:
    band_vars = [v for v in ds.data_vars if v.startswith("Oa")]
    da = ds[band_vars].to_array(dim="bands")  # (bands, y, x) or (bands, t, y, x)

    # Ensure band names are something nice (B01, B02, … or original Oa01,…)
    da = da.assign_coords(bands=band_vars)

    # Optionally attach CRS if you have it
    # da.rio.write_crs("epsg:4326", inplace=True)

    return da

