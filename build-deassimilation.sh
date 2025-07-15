#!/bin/bash

# Delete the old virtual environment

rm -rf .venv

# Delete the cached objects managed by pip... If we don't do this, we are in danger of
# our library builds not working properly due to cached version

pip3 cache purge

# Build a new virtual environment and activate it

python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip to the latest version and load all the default requirements

pip install --upgrade pip
pip install -r dev_requirements.txt

# Build the deassimilate Utils Library

cd deassimilateUtils
rm -rf build dist *.egg-info
python -m build
pip install .

# Copy the deassimilate.py as a symlink into .venv/bin

cd ..
ln -s ../../deassimilate.py .venv/bin/deassimilate
