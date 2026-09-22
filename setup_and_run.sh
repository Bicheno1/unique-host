#!/usr/bin/env bash
# Unique Host - one-shot setup and run for Linux/Mac.
# Creates a virtual environment, installs dependencies, downloads language data, starts the app.
set -e

cd "$(dirname "$0")"

on_error() {
    echo
    echo "Something went wrong. Read the messages above."
    read -p "Press Enter to close..."
    exit 1
}
trap on_error ERR

FIRST_RUN=0

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    FIRST_RUN=1
    if command -v python3.12 >/dev/null 2>&1; then
        python3.12 -m venv venv
    else
        echo "Python 3.12 not found, using default python3 instead."
        python3 -m venv venv
    fi
fi

source venv/bin/activate
python --version

if [ "$FIRST_RUN" = "1" ]; then
    echo "Installing dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

    echo "Downloading spaCy model..."
    python -m spacy download en_core_web_sm

    echo "Downloading NLTK data..."
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
fi

echo
echo "Starting Unique Host. Open the local URL printed below in your browser."
echo "Press Ctrl+C in this window to stop it."
echo
python displayer/app.py
