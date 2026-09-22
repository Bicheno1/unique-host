@echo off
REM Unique Host - one-shot setup and run for Windows.
REM Creates a virtual environment, installs dependencies, downloads language data, starts the app.
REM The window stays open at the end so you can read any error message.
cd /d "%~dp0"

set "FIRST_RUN=0"

if not exist venv (
    echo Creating virtual environment...
    set "FIRST_RUN=1"
    py -3.12 -m venv venv 2>nul
    if errorlevel 1 (
        echo Python 3.12 not found via "py", using default python instead.
        python -m venv venv
        if errorlevel 1 goto :fail
    )
)

call "venv\Scripts\activate.bat"
python --version

if "%FIRST_RUN%"=="1" (
    echo Installing dependencies...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 goto :fail

    echo Downloading spaCy model...
    python -m spacy download en_core_web_sm
    if errorlevel 1 goto :fail

    echo Downloading NLTK data...
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
    if errorlevel 1 goto :fail
)

echo.
echo Starting Unique Host. Open the local URL printed below in your browser.
echo Press Ctrl+C in this window to stop it.
echo.
python displayer\app.py
if errorlevel 1 goto :fail
goto :end

:fail
echo.
echo Something went wrong. Read the messages above.

:end
pause
