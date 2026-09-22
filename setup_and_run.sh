#!/usr/bin/env bash
# One-shot: install dependencies, download language data, start the app.
set -e
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
python displayer/app.py
