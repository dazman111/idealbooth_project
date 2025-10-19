@echo off
REM ------------------------------
REM Script pour supprimer les comptes expirés et créer un log quotidien
REM ------------------------------

REM Récupérer la date du jour au format YYYY-MM-DD
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set today=%%c-%%b-%%a

REM Se placer dans le dossier du projet
cd C:\Users\Daz\Desktop\Photobooths_Project\photobooth_project

REM Exécuter la commande Django et créer un log avec la date
C:\Python312\python.exe manage.py delete_expired_accounts >> deleted_accounts_%today%.log 2>&1
