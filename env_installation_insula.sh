#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Insula / Destination Earth JupyterHub setup for openEO client + DEDL plugin
#
# Expected workflow for a fresh Insula user:
#   git clone https://github.com/suriyahgit/openeo_dedl_plugin.git
#   cd openeo_dedl_plugin
#   bash env_installation_insula.sh
#
# Creates venv: ~/.venvs/openeo_dedl_venv
# Installs (order is important):
#   1) openeo-python-client (branch: dedl_trial) editable
#   2) openeo-processes-dask[implementations] (+ matching GDAL if available)
#   3) THIS repo (openeo_dedl_plugin) editable (assumed: main)
#   4) ipykernel + kernel registration
#   5) extra deps: ascat lxml python-geotiepoints cartopy, etc.
# -----------------------------------------------------------------------------

VENV_NAME="openeo_dedl_venv"
VENV_DIR="${HOME}/.venvs/${VENV_NAME}"

# Keep external clones in one place
SRC_DIR="${HOME}/DEDL_openEO"
CLIENT_REPO_URL="https://github.com/suriyahgit/openeo-python-client.git"
CLIENT_BRANCH="dedl_trial"

# Repo root = directory containing this script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> (0) Prereqs (safe)"
python3 -m pip install --user -U pip virtualenv || true

echo "==> (1) Create venv: ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "==> (2) Upgrade tooling inside venv"
python -m pip install -U pip setuptools wheel

echo "==> (3) Prepare source directory for client clone: ${SRC_DIR}"
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

echo "==> (6) Install openeo-processes-dask[implementations] + GDAL matching system"
if command -v gdal-config >/dev/null 2>&1; then
  GDAL_VER="$(gdal-config --version)"
  echo "    Detected GDAL via gdal-config: ${GDAL_VER}"
  pip install "gdal==${GDAL_VER}" "openeo-processes-dask[implementations]"
else
  echo "    WARNING: gdal-config not found. Installing openeo-processes-dask[implementations] without pinning GDAL."
  echo "    If GDAL wheels fail, you may need to load/enable system GDAL or use a provided module in Insula."
  pip install "openeo-processes-dask[implementations]"
fi

echo "==> (7) Install openeo_dedl_plugin (THIS repo) editable (current branch)"
cd "${REPO_ROOT}"
git fetch --all --prune || true
git pull --ff-only || true

pip install -e .

echo "==> (8) Install ipykernel and register Jupyter kernel"
python -m pip install -U ipykernel
python -m ipykernel install --user \
  --name "${VENV_NAME}" \
  --display-name "Python (${VENV_NAME})"

echo "==> (9) Extra deps"
pip install -U \
  ascat \
  lxml \
  python-geotiepoints \
  cartopy \
  "destinelab>=1.1" \
  "numpy==1.26.4" \
  ipywidgets \
  earthkit-maps \
  earthkit-data \
  earthkit-regrid \
  cf-units

echo ""
echo "✅ Done."
echo "Now reload Jupyter (or refresh kernel list) and choose kernel: Python (${VENV_NAME})"
echo "Venv path: ${VENV_DIR}"
