pyinstaller --onefile --add-data "templates/*;templates" --icon=replay.ico --add-data "static/*;static" --add-data "ffmpeg/*;ffmpeg" --hidden-import=stb --hidden-import=waitress app.py
copy dist\app.exe .\MacReplay.exe
pause
