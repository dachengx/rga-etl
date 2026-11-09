@echo off
cd /d "%~dp0"
docker compose up -d --build
start "" "http://localhost:8000/"
