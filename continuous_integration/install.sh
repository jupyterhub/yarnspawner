#!/usr/bin/env bash
set -xe

conda install -c conda-forge jupyterhub jupyterlab notebook -y

pip install skein pytest pytest-asyncio flake8 conda-pack

cd ~/yarnspawner
pip install -v --no-deps .

conda list
