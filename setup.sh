#!/bin/bash

# Get the base conda path
CONDA_PATH=$(conda info --base)

# Create conda environment
echo "Creating conda environment at $CONDA_PATH/envs/genparse"
conda create -n genparse python=3.10 -y

source "$CONDA_PATH/etc/profile.d/conda.sh"

# Activate the new environment
conda activate genparse

# Verify environment activation
echo "Conda environment 'genparse' activated"
which python

# Install requirements
echo "Installing requirements"
python -m pip install flask waitress

# Clone and install genparse
echo "Installing genparse"
git clone git@github.com:probcomp/genparse.git
cd genparse
make env

# Print success message
echo -e "\n\n"
echo "Setup complete. A conda environment has been created at $CONDA_PATH/envs/genparse."
echo "Activate this environment with 'conda activate genparse'."
echo "Then start the server with 'sh start.sh'."
