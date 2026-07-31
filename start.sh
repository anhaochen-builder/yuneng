#!/bin/bash
cd /home/an/项目/驭能
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 2>&1 | tee /tmp/yuneng.log
