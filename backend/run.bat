@echo off
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=*
cd /d D:\pycharm\t2sAnalysis\backend
uvicorn main:app --host 0.0.0.0 --port 8000
