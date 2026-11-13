#!/usr/bin/env python3
"""Deliver a complete AI render and its recovery map to the local review editor."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request


def request(base, path, value=None, token=None):
    req = urllib.request.Request(base+path, json.dumps(value).encode() if value else None,
                                 {'Content-Type':'application/json','X-Reel-Token':token or ''})
    with urllib.request.urlopen(req) as response:
        return json.load(response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Skill project folder with raw/raw.json and raw/edl.json')
    parser.add_argument('--edit', help='Finished portrait MP4, including graphics and audio')
    parser.add_argument('--name',default='My video')
    parser.add_argument('--notes',help='Read notes and locked cuts from a review project ID')
    parser.add_argument('--url',default='http://127.0.0.1:4318')
    args=parser.parse_args()
    state=request(args.url,'/api/state')
    if state.get('app')!='reel-studio':
        parser.error('This address is not the review editor.')
    if args.notes:
        p=request(args.url,f'/api/projects/{args.notes}/handoff')
        print(json.dumps({'project':p['id'],'source':p['source'],'notes':p['notes'],
                          'clips':p['clips'],'rendered':p.get('rendered')},ensure_ascii=False,indent=2))
        return
    if not args.project or not args.edit:
        parser.error('Supply both --project and --edit, or use --notes ID.')
    result=request(args.url,'/api/import',{'path':str(Path(args.project).expanduser().resolve()),
                  'edit':str(Path(args.edit).expanduser().resolve()),'name':args.name},state['token'])
    print(json.dumps({'project':result['project']['id'],'url':args.url+'/?project='+result['project']['id'],
                      'preparation_job':result['job']['id']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
