@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building executable...
pyinstaller --onefile --windowed --icon=pinoo_icon.ico pinoo_script.py

echo Done!
pause
