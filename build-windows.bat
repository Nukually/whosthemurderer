@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --onefile --name whosthemurder --add-data "data/scripts;data/scripts" -m frontend.main

echo.
echo Build complete. Output: dist\whosthemurder.exe
pause
