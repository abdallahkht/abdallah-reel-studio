#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

URL='http://127.0.0.1:4318'
def ready():
    try:
        with urllib.request.urlopen(URL+'/api/state',timeout=1) as response:
            data=json.load(response)
            return data.get('app')=='reel-studio'
    except Exception:return False

if ready():
    webbrowser.open(URL)
    print('Reel Studio is already running at '+URL)
else:
    process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py'))])
    try:
        for i in range(100):
            if process.poll() is not None:sys.exit(process.returncode)
            if ready():break
            time.sleep(.1)
        webbrowser.open(URL)
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
