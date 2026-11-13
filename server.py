#!/usr/bin/env python3
"""Abdallah Reel Studio: local, non-destructive portrait editing. Python 3.10+, FFmpeg."""
import argparse
import base64
import copy
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('REEL_STUDIO_DATA', ROOT / '_deploy' / 'workspace')).resolve()
LOCK = threading.RLock()
PICKER_LOCK = threading.Lock()
JOBS = {}
TOKEN = uuid.uuid4().hex


def uid():
    return uuid.uuid4().hex[:12]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.writing')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def folder(pid):
    if not re.fullmatch(r'[a-f0-9]{12}', pid):
        raise ValueError('Invalid project ID')
    return DATA / 'projects' / pid


def project(pid):
    return read(folder(pid) / 'project.json')


def run(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace')[-3500:])
    return result.stdout


def preferences():
    path = DATA/'preferences.json'
    return read(path) if path.exists() else {}


def export_directory(value):
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError('Choose an existing folder on this computer.')
    if not os.access(path, os.W_OK):
        raise ValueError('This folder is not writable. Choose another folder.')
    return path


def export_filename(value):
    name = str(value).strip()
    if not name or name in ['.','..'] or len(name)>180 or re.search(r'[\\/:*?"<>|\x00-\x1f]',name):
        raise ValueError('Use a file name without slashes or special path characters.')
    return name if name.lower().endswith('.mp4') else name+'.mp4'


def save_export(source, directory, filename):
    """Never overwrite an existing video, including another export in progress."""
    directory=export_directory(directory)
    filename=export_filename(filename)
    for number in range(1,10000):
        name=filename if number==1 else f'{Path(filename).stem} ({number}).mp4'
        destination=directory/name
        try:
            with destination.open('xb') as target, Path(source).open('rb') as original:
                shutil.copyfileobj(original,target,1024*1024)
            return destination
        except FileExistsError:
            continue
    raise ValueError('Too many exports with this name. Choose a different name.')


def choose_export_folder():
    """Open the operating system's folder picker only on the user's click."""
    if not PICKER_LOCK.acquire(blocking=False):
        raise ValueError('The folder picker is already open.')
    try:
        if sys.platform == 'darwin':
            # AppKit directly: no Finder Apple Events or Automation permission.
            script = """
ObjC.import('AppKit');
function run() {
    var app = $.NSApplication.sharedApplication;
    app.setActivationPolicy($.NSApplicationActivationPolicyAccessory);
    var panel = $.NSOpenPanel.openPanel;
    panel.title = 'Choose export folder';
    panel.prompt = 'Choose';
    panel.canChooseDirectories = true;
    panel.canChooseFiles = false;
    panel.canCreateDirectories = true;
    panel.allowsMultipleSelection = false;
    app.activateIgnoringOtherApps(true);
    return panel.runModal === $.NSModalResponseOK ? ObjC.unwrap(panel.URL.path) : '';
}
"""
            args = ['osascript', '-l', 'JavaScript', '-e', script]
        elif sys.platform == 'win32':
            script = 'Add-Type -AssemblyName System.Windows.Forms; $picker=New-Object System.Windows.Forms.FolderBrowserDialog; if($picker.ShowDialog() -eq "OK"){[Console]::Write($picker.SelectedPath)}'
            args = ['powershell', '-NoProfile', '-STA', '-Command', script]
        else:
            script = 'import tkinter as t; from tkinter import filedialog; r=t.Tk(); r.withdraw(); print(filedialog.askdirectory(title="Choose export folder")); r.destroy()'
            args = [sys.executable, '-c', script]
        result = subprocess.run(args, capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise ValueError('Could not open the system folder picker. Please try again.')
        if not result.stdout.strip():
            return {'cancelled': True}
        return {'directory': str(export_directory(result.stdout.strip()))}
    except subprocess.TimeoutExpired:
        raise ValueError('Folder selection timed out. Click Choose folder to try again.')
    finally:
        PICKER_LOCK.release()


def probe(path):
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
    video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise ValueError('This file has no video stream')
    w, h = video['width'], video['height']
    rotation = next((d.get('rotation', 0) for d in video.get('side_data_list', []) if 'rotation' in d), 0)
    if abs(rotation) % 180 == 90:
        w, h = h, w
    return {'width': w, 'height': h, 'duration': float(info['format']['duration']),
            'fps': float(Fraction(video.get('avg_frame_rate', '30/1')) or 30),
            'audio': any(s['codec_type'] == 'audio' for s in info['streams'])}


def duration(p):
    return sum(c['end'] - c['start'] for c in p['clips'] if c['enabled'])


def playback(p):
    """Use the finished AI edit where it exists; recover uncovered ranges from raw."""
    result, output = [], 0.0
    rendered = p.get('rendered')
    mapping = sorted(rendered['mapping'], key=lambda m: m['sourceStart']) if rendered else []
    for clip in p['clips']:
        if not clip['enabled']:
            continue
        cursor = clip['start']
        def add(start, end, item=None):
            nonlocal output
            if end-start < .000001:
                return
            media_start = item['editStart'] + start-item['sourceStart'] if item else start
            result.append({'clipId': clip['id'], 'kind': 'edit' if item else 'source',
                           'path': rendered['path'] if item else p['source'],
                           'audio': rendered['media']['audio'] if item else p['media']['audio'],
                           'start': media_start, 'end': media_start+end-start,
                           'sourceStart': start, 'sourceEnd': end, 'out': output})
            output += end-start
        for m in mapping:
            start, end = max(cursor, m['sourceStart']), min(clip['end'], m['sourceEnd'])
            if end <= start:
                continue
            add(cursor, start)
            add(start, end, m)
            cursor = end
        add(cursor, clip['end'])
    return result


def attach_render(p, path):
    final = Path(path).expanduser().resolve()
    info = probe(final)
    if abs(info['width']/info['height']-9/16) > .015:
        raise ValueError('The finished edit must be 9:16.')
    if abs(info['duration']-duration(p)) > .04:
        raise ValueError('Finished-video duration does not match the cut map. Supply the exact EDL used for this render.')
    mapping, out = [], 0.0
    for c in p['clips']:
        if c['enabled']:
            mapping.append({'sourceStart': c['start'], 'sourceEnd': c['end'], 'editStart': out})
            out += c['end']-c['start']
    # Duplicate/overlapping source ranges cannot be matched unambiguously after restoration.
    ordered = sorted(mapping, key=lambda m:m['sourceStart'])
    if any(a['sourceEnd'] > b['sourceStart']+.001 for a,b in zip(ordered,ordered[1:])):
        raise ValueError('The recovery map must not contain overlapping source ranges.')
    p['rendered'] = {'path': str(final), 'media': info, 'mapping': mapping}


def make_thumbnails(source, target, seconds):
    run(['ffmpeg','-v','error','-nostdin','-i',str(source),'-vf',
         f'fps={20/max(seconds,.1)},scale=90:160,tile=20x1','-frames:v','1','-q:v','4',str(target)])


def waveform(source, audio=True):
    if not audio:
        return []
    import array
    samples = array.array('h', run(['ffmpeg','-v','error','-i',str(source),'-vn','-ac','1','-ar','4000','-f','s16le','-']))
    step = max(1,len(samples)//1200)
    return [round(max(abs(v) for v in samples[i:i+step])/32768,4) for i in range(0,len(samples),step)]


def validate(p):
    total = p['media']['duration']
    if not isinstance(p.get('clips'), list) or not 1 <= len(p['clips']) <= 500:
        raise ValueError('A project needs 1–500 source clips')
    ids = set()
    for c in p['clips']:
        if not isinstance(c.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', c['id']):
            raise ValueError('Invalid clip ID')
        if c['id'] in ids:
            raise ValueError('Duplicate clip ID')
        ids.add(c['id'])
        for k in ['start', 'end']:
            c[k] = float(c[k])
            if not math.isfinite(c[k]):
                raise ValueError('Invalid source time')
        if not 0 <= c['start'] < c['end'] <= total + .01 or c['end'] - c['start'] < 1/30 - .0001:
            raise ValueError('Keep at least one frame within the original footage')
        c['enabled'] = bool(c.get('enabled', True))
        c['locked'] = bool(c.get('locked', False))
    if duration(p) < 1/30:
        raise ValueError('Keep at least one clip in the Reel')
    if len(p.get('graphics', [])) > 80:
        raise ValueError('Maximum 80 graphics per project')
    for g in p.get('graphics', []):
        if not isinstance(g.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', g['id']):
            raise ValueError('Invalid graphic ID')
        if g.get('type') not in ['title', 'stat', 'checklist', 'caption']:
            raise ValueError('Unknown graphic type')
        for k in ['start', 'end']:
            g[k] = float(g[k])
            if not math.isfinite(g[k]):
                raise ValueError('Invalid graphic time')
        if not 0 <= g['start'] < g['end'] <= duration(p) + .01:
            raise ValueError('Graphic timing must fit the edited Reel. Adjust it before shortening the Reel.')
        if len(g.get('text', '')) > 500:
            raise ValueError('Graphic text is too long (maximum 500 characters)')
        png = g.get('image', '')
        if png and (not png.startswith('data:image/png;base64,') or len(png) > 2000000):
            raise ValueError('Invalid graphic artwork')
    if len(p.get('notes', [])) > 500:
        raise ValueError('Maximum 500 notes')
    for n in p.get('notes', []):
        if not isinstance(n.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', n['id']):
            raise ValueError('Invalid note ID')
        if n.get('mode') not in ['source', 'edit'] or not math.isfinite(float(n.get('time', -1))) or float(n['time']) < 0:
            raise ValueError('Invalid note time')


def save(pid, incoming, reason='Manual edit', actor='human'):
    with LOCK:
        current = project(pid)
        if incoming.get('revision') != current['revision']:
            raise ValueError('This project changed elsewhere. Reload before saving to preserve both edits.')
        updated = copy.deepcopy(current)
        for key in ['name', 'clips', 'graphics', 'notes']:
            if key in incoming:
                updated[key] = incoming[key]
        if actor == 'ai':
            new_by_id = {c['id']: c for c in updated['clips']}
            for c in current['clips']:
                if c.get('locked') and new_by_id.get(c['id']) != c:
                    raise ValueError('AI update would change a locked clip: ' + c['id'])
        validate(updated)
        updated['revision'] += 1
        updated['updated'] = time.time()
        updated['reason'] = str(reason)[:180]
        write(folder(pid) / 'revisions' / f"{updated['revision']:05}.json", updated)
        write(folder(pid) / 'project.json', updated)
        return updated


def job(kind, pid, operation):
    jid = uid()
    JOBS[jid] = {'id': jid, 'kind': kind, 'project': pid, 'state': 'running', 'progress': 'Starting…'}
    def work():
        try:
            result = operation(JOBS[jid])
            JOBS[jid].update(state='done', result=result, progress='Ready')
        except Exception as exc:
            JOBS[jid].update(state='error', error=str(exc))
    threading.Thread(target=work, daemon=True).start()
    return JOBS[jid]


def prepare(pid, status):
    p = project(pid)
    target = folder(pid)
    status['progress'] = 'Preparing a lightweight portrait preview…'
    run(['ffmpeg', '-v', 'error', '-nostdin', '-i', p['source'], '-vf', 'scale=540:960,setsar=1',
         '-r', '30', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(target / 'preview.mp4')])
    status['progress'] = 'Reading the audio waveform…'
    peaks = []
    if p['media']['audio']:
        import array
        samples = array.array('h', run(['ffmpeg', '-v', 'error', '-i', p['source'], '-vn', '-ac', '1', '-ar', '4000', '-f', 's16le', '-']))
        step = max(1, len(samples) // 1200)
        peaks = [round(max(abs(v) for v in samples[i:i+step]) / 32768, 4) for i in range(0, len(samples), step)]
    write(target / 'waveform.json', peaks)
    make_thumbnails(p['source'], target/'source-thumbs.jpg', p['media']['duration'])
    if p.get('rendered'):
        status['progress'] = 'Opening the finished edit…'
        run(['ffmpeg','-v','error','-nostdin','-i',p['rendered']['path'],'-vf','scale=540:960,setsar=1',
             '-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','160k','-movflags','+faststart',str(target/'edit-preview.mp4')])
        make_thumbnails(p['rendered']['path'],target/'edit-thumbs.jpg',p['rendered']['media']['duration'])
        write(target/'edit-waveform.json',waveform(p['rendered']['path'],p['rendered']['media']['audio']))
    return {'preview': f'/media/{pid}/preview.mp4'}


def import_project(body):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('Install FFmpeg and ffprobe, then restart Abdallah Reel Studio. See the setup instructions in README.md.')
    source = Path(body['path']).expanduser().resolve()
    clips, transcript, origin = [], [], None
    if source.is_dir():
        origin = str(source)
        raw = source / 'raw' / 'raw.json'
        edl = source / 'raw' / 'edl.json'
        if not raw.exists() or not edl.exists():
            raise ValueError('Skill project needs raw/raw.json and raw/edl.json. You can import a portrait video instead.')
        meta, cuts = read(raw), read(edl)
        source = Path(meta['source']).expanduser()
        if not source.is_absolute():
            source = Path(origin) / source
        fps = float(cuts.get('fps', 30))
        for i, c in enumerate(cuts['pieces']):
            start = float(c.get('src', c.get('f0', 0)/fps))
            clips.append({'id': uid(), 'label': f'Take {i+1:02}', 'start': start, 'end': start + c['n']/fps,
                          'enabled': True, 'locked': False})
        chunks = Path(origin) / 'raw' / 'chunks.json'
        if chunks.exists():
            transcript = read(chunks)
            if not isinstance(transcript, list):
                transcript = transcript.get('chunks', [])
    if not source.is_file():
        raise ValueError('Video not found. Use the full local file path.')
    media = probe(source)
    if abs(media['width']/media['height'] - 9/16) > .015:
        raise ValueError('This first version accepts 9:16 footage. Import a portrait source or crop a separate copy first.')
    pid = uid()
    p = {'schema': 1, 'id': pid, 'name': body.get('name') or (Path(origin).name if origin else source.stem),
         'source': str(source), 'origin': origin, 'media': media, 'fps': 30, 'revision': 1,
         'updated': time.time(), 'reason': 'Imported source and AI cuts' if origin else 'Imported original footage',
         'clips': clips or [{'id': uid(), 'label': 'Original take', 'start': 0, 'end': media['duration'], 'enabled': True, 'locked': False}],
         'graphics': [], 'notes': [], 'transcript': transcript}
    validate(p)
    if body.get('edit'):
        attach_render(p, body['edit'])
    write(folder(pid)/'project.json', p)
    write(folder(pid)/'revisions'/'00001.json', p)
    return {'project': p, 'job': job('prepare', pid, lambda s: prepare(pid, s))}


def export_project(p, status, settings=None):
    settings = settings or {}
    height = int(settings.get('height', 1920))
    if height not in [1280,1920,2560,3840]:
        raise ValueError('Choose 720p, 1080p, 1440p, or 4K.')
    width = height*9//16
    fps = int(settings.get('fps',30))
    if fps not in [24,25,30,50,60]:
        raise ValueError('Choose a supported frame rate.')
    crf = {'draft':'26','standard':'20','high':'16'}[settings.get('quality','high')]
    destination = export_directory(settings['directory']) if settings.get('directory') else None
    filename = export_filename(settings.get('filename','reel.mp4'))
    pid = p['id']
    out = folder(pid) / 'exports' / f"r{p['revision']}-{uid()}"
    out.mkdir(parents=True)
    write(out / 'project.json', p)
    parts = []
    active = []
    for segment in playback(p):
        if active and active[-1]['path']==segment['path'] and abs(active[-1]['end']-segment['start'])<.000001:
            active[-1]['end']=segment['end']
        else:
            active.append(dict(segment))
    for i, c in enumerate(active):
        status['progress'] = f'Rendering source clip {i+1} of {len(active)}…'
        part = out / f'part-{i:03}.mkv'
        args = ['ffmpeg', '-v', 'error', '-nostdin', '-ss', str(c['start']), '-i', c['path']]
        if not c['audio']:
            args += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
        args += ['-t', str(c['end']-c['start']), '-map', '0:v:0', '-map', '0:a:0' if c['audio'] else '1:a:0',
                 '-vf', f'scale={width}:{height},setsar=1,fps={fps}', '-af', 'aresample=48000,asetpts=PTS-STARTPTS',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', crf, '-pix_fmt', 'yuv420p',
                 '-c:a', 'pcm_s16le', '-ac', '2', str(part)]
        run(args)
        parts.append(part)
    # Relative controlled names avoid quoting arbitrary source paths in concat files.
    (out/'concat.txt').write_text('\n'.join(f"file '{f.name}'" for f in parts))
    joined = out / 'cuts.mp4'
    run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'concat', '-safe', '1', '-i', str(out/'concat.txt'),
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(joined)])
    final = out / 'reel.mp4'
    if p['graphics']:
        status['progress'] = 'Compositing animated graphics…'
        args = ['ffmpeg', '-v', 'error', '-nostdin', '-i', str(joined)]
        filters = []
        previous = '0:v'
        for i, g in enumerate(p['graphics']):
            if not g.get('image'):
                raise ValueError('Open the project and Save once to prepare graphic artwork before export.')
            png = out / f'graphic-{i}.png'
            png.write_bytes(base64.b64decode(g['image'].split(',', 1)[1], validate=True))
            args += ['-loop', '1', '-framerate', str(fps), '-i', str(png)]
            start, end = g['start'], g['end']
            fade = min(.24, (end-start)/3)
            filters.append(f'[{i+1}:v]scale={width}:{height},format=rgba,fade=t=in:st={start}:d={fade}:alpha=1,fade=t=out:st={end-fade}:d={fade}:alpha=1[g{i}]')
            filters.append(f'[{previous}][g{i}]overlay=0:0:enable=\'between(t,{start},{end})\'[v{i}]')
            previous = f'v{i}'
        args += ['-filter_complex', ';'.join(filters), '-map', f'[{previous}]', '-map', '0:a:0',
                 '-t', str(duration(p)), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', crf,
                 '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(final)]
        run(args)
    else:
        shutil.copy2(joined, final)
    delivered = save_export(final,destination,filename) if destination else final
    result = {'url': f'/media/{pid}/exports/{out.name}/reel.mp4', 'path': str(delivered),
              'filename':delivered.name, 'revision': p['revision'], 'media': probe(final)}
    write(out/'delivery.json',result)
    if destination:
        with LOCK:
            saved=preferences();saved['export_directory']=str(destination);write(DATA/'preferences.json',saved)
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ['200', '206']:
            super().log_message(fmt, *args)

    def json(self, value, code=200):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self):
        host = self.headers.get('Host', '')
        return host in [f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}']

    def do_GET(self):
        if not self.allowed():
            return self.json({'error': 'Local access only'}, 403)
        path = unquote(urlparse(self.path).path)
        bits = path.strip('/').split('/')
        try:
            if path == '/api/state':
                projects = []
                for f in (DATA/'projects').glob('*/project.json'):
                    p = read(f)
                    projects.append({k: p[k] for k in ['id', 'name', 'revision', 'updated']})
                return self.json({'app': 'reel-studio', 'token': TOKEN, 'projects': sorted(projects, key=lambda p:p['updated'], reverse=True),
                                  'ffmpeg': bool(shutil.which('ffmpeg')), 'version': '0.1.0'})
            if path == '/api/export-preferences':
                return self.json(preferences())
            if len(bits) == 3 and bits[:2] == ['api', 'projects']:
                p = project(bits[2])
                p['previewReady'] = (folder(p['id'])/('edit-thumbs.jpg' if p.get('rendered') else 'waveform.json')).exists()
                p['preparation'] = next((j for j in reversed(list(JOBS.values())) if j['project'] == p['id'] and j['kind'] == 'prepare'), None)
                return self.json(p)
            if len(bits) == 4 and bits[:2] == ['api', 'projects'] and bits[3] == 'history':
                exports = {}
                for f in sorted((folder(bits[2])/'exports').glob('*/reel.mp4')):
                    snapshot = read(f.parent/'project.json')
                    exports.setdefault(snapshot['revision'], []).append(f'/media/{bits[2]}/exports/{f.parent.name}/reel.mp4')
                return self.json([{'revision':p['revision'], 'reason':p['reason'], 'updated':p['updated'], 'exports':exports.get(p['revision'], [])} for p in
                                  [read(f) for f in sorted((folder(bits[2])/'revisions').glob('*.json'), reverse=True)]])
            if len(bits) == 3 and bits[:2] == ['api', 'jobs']:
                return self.json(JOBS[bits[2]])
            if len(bits) == 4 and bits[:2] == ['api', 'projects'] and bits[3] == 'handoff':
                p = project(bits[2])
                p['instructions'] = 'Use your existing editing skill. Keep original source immutable. Times are source seconds; graphics use edited-output seconds. Locked clips must remain identical. POST {project,actor:"ai",reason} with current revision to /api/projects/ID/save. Read app README and bridge skill.'
                return self.json(p)
            if bits[0] == 'media' and len(bits) >= 3:
                base = folder(bits[1]).resolve()
                file = (base / '/'.join(bits[2:])).resolve()
                if not file.is_relative_to(base) or file.suffix not in ['.mp4', '.json', '.jpg']:
                    raise ValueError('Invalid media path')
                return self.file(file)
            file = ROOT/'web'/('index.html' if path == '/' else path.lstrip('/'))
            if not file.resolve().is_relative_to((ROOT/'web').resolve()):
                raise ValueError('Invalid file path')
            return self.file(file)
        except (ValueError, KeyError, FileNotFoundError) as exc:
            self.json({'error': str(exc)}, 404)

    def file(self, path):
        size = path.stat().st_size
        start, end, code = 0, size-1, 200
        requested = self.headers.get('Range')
        if requested:
            m = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not m or not any(m.groups()):
                return self.json({'error': 'Unsupported range'}, 416)
            if m[1]:
                start, end = int(m[1]), min(int(m[2]) if m[2] else size-1, size-1)
            else:
                start = max(0, size-int(m[2]))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(end-start+1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        if code == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as f:
                f.seek(start)
                remaining = end-start+1
                while remaining:
                    block = f.read(min(262144, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self.allowed() or self.headers.get('X-Reel-Token') != TOKEN:
            return self.json({'error': 'Refresh the local editor to reconnect'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin not in [f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}']:
            return self.json({'error': 'Local access only'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if urlparse(self.path).path == '/api/upload':
                name = Path(unquote(self.headers.get('X-Filename','video.mp4'))).name
                if Path(name).suffix.lower() not in ['.mp4','.mov','.mkv','.webm','.m4v'] or not 0 < length <= 10_000_000_000:
                    raise ValueError('Choose a video file up to 10 GB.')
                target = DATA/'imports'/uid()/name
                target.parent.mkdir(parents=True)
                with target.open('xb') as f:
                    remaining = length
                    while remaining:
                        block = self.rfile.read(min(1024*1024,remaining))
                        if not block:
                            raise ValueError('Upload interrupted. Select the video again.')
                        f.write(block)
                        remaining -= len(block)
                return self.json(import_project({'path':str(target)}))
            if length > 20_000_000:
                raise ValueError('Request is too large')
            body = json.loads(self.rfile.read(length))
            bits = urlparse(self.path).path.strip('/').split('/')
            if bits == ['api','choose-export-folder']:
                return self.json(choose_export_folder())
            if bits == ['api', 'import']:
                return self.json(import_project(body))
            if len(bits) == 4 and bits[:2] == ['api', 'projects']:
                pid, action = bits[2:]
                if action == 'save':
                    return self.json(save(pid, body['project'], body.get('reason', 'Manual edit'), body.get('actor', 'human')))
                if action == 'restore':
                    old = read(folder(pid)/'revisions'/f"{int(body['target']):05}.json")
                    old['revision'] = body['revision']
                    return self.json(save(pid, old, f"Restored revision {body['target']}"))
                if action == 'export':
                    p = project(pid)
                    if body['revision'] != p['revision']:
                        raise ValueError('Save or reload before exporting')
                    settings=body.get('settings') or {}
                    if settings.get('directory'):
                        export_directory(settings['directory'])
                    export_filename(settings.get('filename','reel.mp4'))
                    return self.json(job('export', pid, lambda s: export_project(p, s, body.get('settings'))))
                if action == 'prepare':
                    if (folder(pid)/'preview.mp4').exists():
                        raise ValueError('Preview already exists. Check preparation errors before retrying.')
                    return self.json(job('prepare', pid, lambda s: prepare(pid, s)))
            raise ValueError('Unknown action')
        except Exception as exc:
            self.json({'error': str(exc)}, 400)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4318)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Abdallah Reel Studio → http://127.0.0.1:{args.port}', flush=True)
    print(f'Projects: {DATA}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
