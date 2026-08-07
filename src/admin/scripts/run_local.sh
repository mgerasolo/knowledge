#!/bin/bash
# Run Admin API locally for development

set -e

cd "$(dirname "$0")/.."

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your database credentials"
    exit 1
fi

# Load environment
source .env

# Install dependencies
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Run in debug mode
export FLASK_DEBUG=true
python app.py
