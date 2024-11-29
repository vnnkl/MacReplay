pyinstaller --onefile --add-data "templates/*;templates" --icon=icon.ico --add-data "static/*;static" --add-data "ffmpeg/ffmpeg.exe;." --add-data "ffmpeg/ffprobe.exe;." --hidden-import=stb --hidden-import=waitress app.py
copy dist\app.exe .\MacSurge.exe
pause
