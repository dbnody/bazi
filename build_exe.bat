@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/2] 检查 PyInstaller ...
python -m PyInstaller --version >nul 2>&1 || python -m pip install pyinstaller || goto fail
echo [2/2] 打包单文件与便携版 ...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BaziSuite --icon assets\app.ico --paths . main.py || goto fail
python -m PyInstaller --noconfirm --clean --onedir --windowed --name BaziSuite --icon assets\app.ico --paths . --distpath dist-portable main.py || goto fail
if not exist "dist-portable\BaziSuite" goto fail
if exist "dist-portable\八字命理通鉴" rd /s /q "dist-portable\八字命理通鉴"
move /y "dist-portable\BaziSuite" "dist-portable\八字命理通鉴" >nul
ren "dist-portable\八字命理通鉴\BaziSuite.exe" "八字命理通鉴.exe"
if exist "dist\八字命理通鉴.exe" del /q "dist\八字命理通鉴.exe"
move /y "dist\BaziSuite.exe" "dist\八字命理通鉴.exe" >nul
echo.
echo 打包完成：
echo   单文件 dist\八字命理通鉴.exe
echo   便携版 dist-portable\八字命理通鉴\八字命理通鉴.exe
goto end

:fail
echo.
echo 打包失败，请检查上面的报错。
pause
exit /b 1

:end
pause
