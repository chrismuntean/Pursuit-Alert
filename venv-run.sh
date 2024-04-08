#!/bin/bash

# Define the path for the virtual environment and the temporary directory for pip installs
VENV_DIR="pursuit-alert-venv"
PIP_TMP_DIR="pip_tmp"

echo "Setting up the Python virtual environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Trying to install..."
    sudo apt-get update && sudo apt-get install -y python3
    if ! command -v python3 &> /dev/null; then
        echo "Failed to install Python 3. Exiting."
        exit 1
    fi
fi

# Check if python3-venv is installed
if ! python3 -m venv --help &> /dev/null; then
    echo "python3-venv is not installed. Trying to install..."
    sudo apt-get install -y python3-venv
fi

# Check if the virtual environment directory exists and create it if it doesn't
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR

    # Activate the virtual environment
    echo "Activating the virtual environment..."
    source $VENV_DIR/bin/activate

    # Create and use a custom TMPDIR for pip installs
    mkdir -p $PIP_TMP_DIR
    export TMPDIR=$PIP_TMP_DIR

    # Install packages from requirements.txt
    echo "Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # Remove the custom TMPDIR
    rm -rf $PIP_TMP_DIR

    echo "Setup is complete"
else
    # Activate the virtual environment
    echo "Virtual environment already set up. Activating..."
    source $VENV_DIR/bin/activate
fi

# Start Pursuit Alert
echo "Starting the Python application..."
python -m streamlit run Pursuit_Alert.py