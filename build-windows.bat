@echo off
setlocal

python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --onefile --name whosthemurder --add-data "data/scripts;data/scripts" -m frontend.main

echo.
echo Build complete. Output: dist\whosthemurder.exe
pause
