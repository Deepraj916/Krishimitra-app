#!/usr/bin/env bash
# exit on error
set -o errexit

# Install all the Python packages
pip install -r requirements.txt

# Run the script to create the database tables
python create_tables.py