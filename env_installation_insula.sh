#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Insula / Destination Earth JupyterHub setup for openEO client + DEDL plugin
# Creates venv: ~/.venvs/openeo_dedl_venv
# Installs:
#   - openeo-python-client (branch: dedl_trial) editable
#   - openeo-dedl-plugin  (branch: ascat)     editable
#   - openeo-processes-dask[implementations] (+ matching GDAL)
#   - ipykernel + kernel registration
#   - extra deps: ascat lxml python-geotiepoints cartopy
#
# Usage:
#   bash env_installation_insula.sh
# -----------------------------------------------------------------------------

VENV_NAME="openeo_dedl_venv"
VENV_DIR="${HOME}/.venvs/${VENV_NAME}"

# Choose where to clone sources (keeps $HOME tidy and avoids cloning into repo dir)
SRC_DIR="${HOME}/src/dedl"
CLIENT_REPO_URL="https://github.com/suriyahgit/openeo-python-client.git"
CLIENT_BRANCH="dedl_trial"
PLUGIN_REPO_URL="https://github.com/suriyahgit/openeo_dedl_plugin.git"
PLUGIN_BRANCH="ascat"

echo "==> (0) Prereqs (safe)"
python3 -m pip install --user -U pip virtualenv || true

echo "==> (1) Create venv: ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "==> (2) Upgrade tooling inside venv"
python -m pip install -U pip setuptools wheel

echo "==> (3) Prepare source directory: ${SRC_DIR}"
mkdir -p "${SRC_DIR}"
cd "${SRC_DIR}"

echo "==> (4) Clone/update openeo-python-client (branch: ${CLIENT_BRANCH})"
if [[ -d "${SRC_DIR}/openeo-python-client/.git" ]]; then
  cd "${SRC_DIR}/openeo-python-client"
  git fetch --all --prune
else
  git clone "${CLIENT_REPO_URL}" "${SRC_DIR}/openeo-python-client"
  cd "${SRC_DIR}/openeo-python-client"
fi
git checkout "${CLIENT_BRANCH}"
git pull --ff-only || true

echo "==> (5) Install openeo-python-client editable"
pip install -e .

echo "==> (6) Install openeo-processes-dask implementations + GDAL matching system"
if command -v gdal-config >/dev/null 2>&1; then
  GDAL_VER="$(gdal-config --version)"
  echo "    Detected GDAL via gdal-config: ${GDAL_VER}"
  pip install "gdal==${GDAL_VER}" "openeo-processes-dask[implementations]"
else
  echo "    WARNING: gdal-config not found. Installing openeo-processes-dask[implementations] without pinning GDAL."
  echo "    If GDAL wheels fail, you may need to load/enable system GDAL or use a provided module in Insula."
  pip install "openeo-processes-dask[implementations]"
fi

echo "==> (7) Clone/update openeo-dedl-plugin (branch: ${PLUGIN_BRANCH})"
cd "${SRC_DIR}"
if [[ -d "${SRC_DIR}/openeo-dedl-plugin/.git" ]]; then
  cd "${SRC_DIR}/openeo-dedl-plugin"
  git fetch --all --prune
else
  git clone "${PLUGIN_REPO_URL}" "${SRC_DIR}/openeo-dedl-plugin"
  cd "${SRC_DIR}/openeo-dedl-plugin"
fi
git checkout "${PLUGIN_BRANCH}"
git pull --ff-only || true

echo "==> (8) Install openeo-dedl-plugin editable"
pip install -e .

echo "==> (9) Install ipykernel and register Jupyter kernel"
python -m pip install -U ipykernel
python -m ipykernel install --user \
  --name "${VENV_NAME}" \
  --display-name "Python (${VENV_NAME})"

echo "==> (10) Extra deps"
pip install -U ascat lxml python-geotiepoints cartopy

echo ""
echo "✅ Done."
echo "Now reload Jupyter (or refresh kernel list) and choose kernel: Python (${VENV_NAME})"
echo "Venv path: ${VENV_DIR}"

source "${VENV_DIR}/bin/activate"
