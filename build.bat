@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo Building executable with full tkinterdnd2 support...
pyinstaller --onefile --windowed --icon=pinoo_icon.ico ^
    --collect-all tkinterdnd2 ^
    --hidden-import tkinterdnd2 ^
    --hidden-import tkinterdnd2.TkinterDnD ^
    --add-data "%LOCALAPPDATA%\Programs\Python\Python*\Lib\site-packages\tkinterdnd2\tkdnd;tkdnd" ^
    pinoo_script.py

echo Done!
pause