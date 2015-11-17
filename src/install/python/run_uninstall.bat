@echo off
:: provide a batch file so user can double click to install.

:: run the installer in install mode
.\sageplex_install -u

:: pause after installer ended so user can see status before window is
:: closed.
echo.
pause
