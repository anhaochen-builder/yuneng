#!/bin/bash
source /home/an/项目/驭能/venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
