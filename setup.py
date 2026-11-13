#!/usr/bin/env python3
"""Set up the community skills without replacing an existing installation."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Check requirements without installing anything')
    parser.add_argument('--motion',action='store_true',help='Also install optional motion renderer dependencies in .venv')
    args=parser.parse_args()
    missing=[name for name in ['ffmpeg','ffprobe'] if not shutil.which(name)]
    if sys.version_info<(3,10):
        raise SystemExit('Python 3.10 or newer is required.')
    if missing:
        raise SystemExit('Install FFmpeg first (includes ffprobe). See docs/setup-ar.md.')
    if args.check:
        print('Python and FFmpeg are ready.');return
    for home in [Path(os.environ.get('CODEX_HOME',Path.home()/'.codex')),Path.home()/'.claude']:
        for source in sorted((ROOT/'skills').iterdir()):
            if not (source/'SKILL.md').is_file():continue
            target=home/'skills'/source.name
            if target.exists() or target.is_symlink():
                print(f'Kept existing skill: {target}');continue
            target.parent.mkdir(parents=True,exist_ok=True)
            if os.name=='nt':
                shutil.copytree(source,target)
                (target/'app-location.txt').write_text(str(ROOT),encoding='utf-8')
            else:target.symlink_to(source,target_is_directory=True)
            print(f'Installed: {source.name}')
    if args.motion:
        env=ROOT/'.venv'
        if not env.exists():subprocess.run([sys.executable,'-m','venv',str(env)],check=True)
        python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'motion/requirements.txt')],check=True)
    print('Ready. Keep this folder in place. Restart your AI session to discover the skills.')

if __name__=='__main__':main()
