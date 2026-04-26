@echo off
title Fandom Dizi/Film Transkript Indirici
color 0A
echo.
echo ===================================================
echo     FANDOM DIZI/FILM TRANSKRIPT VE GORSEL CEKICI
echo ===================================================
echo Lutfen bekleyin, gereksinimler kontrol ediliyor...
python -m pip install beautifulsoup4 >nul 2>&1
echo Gereksinimler hazir!
echo.
python auto_scraper.py
pause
