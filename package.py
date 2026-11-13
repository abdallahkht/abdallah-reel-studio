#!/usr/bin/env python3
"""Build a member ZIP from tracked release files, never local media or history."""
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parent
VERSION='0.4.4'

def main():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    target=ROOT/'_deploy'/'releases'/f'abdallah-reel-studio-v{VERSION}.zip'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise SystemExit('Release ZIP exists; keep it or choose a new version.')
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for name in filter(None,names):
            path=Path(name)
            if any(part in ['_deploy','.venv','.git','__pycache__'] for part in path.parts):
                raise SystemExit('Runtime data must not be tracked: '+name)
            archive.write(ROOT/path,'abdallah-reel-studio/'+name)
    print(target)

if __name__=='__main__':main()
