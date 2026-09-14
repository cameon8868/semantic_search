@echo off
cd /d "%~dp0"

title Semantic Search - Full Auto Start

echo ============================================================
echo    SEMANTIC SEARCH - FULL AUTO START
echo ============================================================
echo.

REM --- 1. Create venv if missing -----------------------------
if not exist "venv\bin\activate.bat" (
    echo [1/7] Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo       [ERROR] Failed to create venv. Is Python installed?
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [1/7] venv already exists.
)
echo.

REM --- 2. Activate venv --------------------------------------
echo [2/7] Activating venv...
call venv\bin\activate.bat
if errorlevel 1 (
    echo       [ERROR] Failed to activate venv!
    pause
    exit /b 1
)
echo       OK
echo.

REM --- 3. Install dependencies -------------------------------
if exist "requirements.txt" (
    echo [3/7] Installing PyTorch ^(CPU^) with progress...
    echo       Size: ~150 MB, may take 2-5 minutes.
    echo.
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo       [WARNING] PyTorch install failed.
    ) else (
        echo       OK
    )
    echo.

    echo       Installing other dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo       [WARNING] Some dependencies failed to install.
    ) else (
        echo       OK
    )
) else (
    echo [3/7] [WARNING] requirements.txt not found.
)
echo.

REM --- 4. Download corpus if missing -------------------------
if not exist "wikipedia_docs" (
    echo [4/7] wikipedia_docs not found. Running parsing.py...
    parsing.py
    if errorlevel 1 (
        echo       [ERROR] parsing.py failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    dir /b /a-d "wikipedia_docs\*.txt" >nul 2>&1
    if errorlevel 1 (
        echo [4/7] wikipedia_docs is empty. Running parsing.py...
        parsing.py
        if errorlevel 1 (
            echo       [ERROR] parsing.py failed!
            pause
            exit /b 1
        )
        echo       OK
    ) else (
        echo [4/7] wikipedia_docs already populated.
    )
)
echo.

REM --- 5. Build tfidf.exe if missing -------------------------
if not exist "tfidf.exe" (
    echo [5/7] tfidf.exe not found. Building from tfidf.cpp...
    where g++ >nul 2>&1
    if errorlevel 1 (
        echo       [ERROR] g++ not found. Install MinGW or place tfidf.exe manually.
        pause
        exit /b 1
    )
    g++ -std=c++17 tfidf.cpp -o tfidf.exe
    if errorlevel 1 (
        echo       [ERROR] Compilation failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [5/7] tfidf.exe already exists.
)
echo.

REM --- 6. Build vectors.json if missing ----------------------
if not exist "vectors.json" (
    echo [6/7] vectors.json not found. Running tfidf.exe...
    tfidf.exe
    if errorlevel 1 (
        echo       [ERROR] tfidf.exe failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [6/7] vectors.json already exists.
)
echo.

REM --- 7. Start server ---------------------------------------
echo [7/7] Starting FastAPI server...
echo.
echo ============================================================
echo    SERVER STARTED
echo ============================================================
echo    Open:    http://127.0.0.1:8000
echo    Docs:    http://127.0.0.1:8000/docs
echo.
echo    Modes:
echo      - TF-IDF   (lexical)
echo      - SBERT    (semantic)
echo      - Hybrid   (RRF)
echo.
echo    Stop server: Ctrl+C
echo ============================================================
echo.

search_api.py

echo.
echo ============================================================
echo    SERVER STOPPED
echo ============================================================
pause
