# openeo_dedl_plugin/sen3.py

from pathlib import Path
from typing import List, Optional

import xarray as xr


def open_olci_wfr_sen3(path: Path, variables: Optional[List[str]] = None) -> xr.DataArray:
    """
    Open a Sentinel-3 OLCI WFR .SEN3 directory as an xarray.DataArray
    with a 'bands' dimension that is compatible with openEO local processing.

    Parameters
    ----------
    path:
        Path to the .SEN3 directory.
    variables:
        Optional subset of variable names to include. If None, all variables
        starting with 'Oa' are used.

    Returns
    -------
    xarray.DataArray
        Array with dimensions (bands, y, x, ...) depending on the source files.
    """
    path = Path(path)

    if not path.is_dir():
        raise ValueError(f"{path!r} is not a directory. Expected a .SEN3 folder.")

    # This glob pattern is deliberately broad; adjust to the actual filenames
    # in your OLCI WFR products (e.g. *_radiance.nc, *_reflectance.nc, etc.)
    nc_files = sorted(path.glob("Oa*.nc"))
    if not nc_files:
        raise IOError(f"No OLCI band NetCDF files found in {path!s}")

    # Combine by coordinates; if products are tiled differently, you may need 'nested'
    ds = xr.open_mfdataset(
        [str(f) for f in nc_files],
        combine="by_coords",
        parallel=True,
    )

    # Choose band variables
    if variables is None:
        band_vars = [v for v in ds.data_vars if v.startswith("Oa")]
    else:
        band_vars = variables

    if not band_vars:
        raise ValueError(f"No band variables found in dataset from {path!s}")

    # Stack variables into a 'bands' dimension
    da = ds[band_vars].to_array(dim="bands")
    da = da.assign_coords(bands=band_vars)

    # You can attach CRS here if available, e.g.:
    # import rioxarray
    # da = da.rio.write_crs("EPSG:4326", inplace=True)

    return da
