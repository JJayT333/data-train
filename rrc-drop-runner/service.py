"""Local conversion service shared by the browser interface and release launcher."""
import csv
import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import traceback
import uuid
from flask import Flask, abort, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from parsers import ROOT, TOOLS, extract, route
from recognition import recognize, supported_catalog

CAT = supported_catalog()
BY = {d['slug']: d for d in CAT}
DATA = Path(os.environ.get('RRC_DATA_DIR', str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Texas RRC Data Converter')))
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / 'Results'
OUT.mkdir(exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix='rrc-', dir=DATA))
app = Flask(__name__, template_folder=str(Path(ROOT)/'templates'), static_folder=str(Path(ROOT)/'static'))
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024**3
UPLOADS = {}
RESULTS = {}
LOCK = threading.Lock()

def error(message, status=400, details=None):
    return jsonify(error=message, details=details), status

def stage(upload):
    if not upload or not upload.filename: raise ValueError('Choose an RRC data file first.')
    token = uuid.uuid4().hex
    work = WORK / token
    work.mkdir()
    filename = secure_filename(upload.filename) or 'upload'
    path = work / filename
    upload.save(path)
    if not path.stat().st_size: raise ValueError('This file is empty. Choose a data download containing records.')
    source_notes = []
    files = extract(str(path), str(work/'unpacked'), source_notes)
    detection = recognize(files, filename)
    if detection.get('source_note'): source_notes.append(detection['source_note'])
    UPLOADS[token] = dict(files=files, filename=upload.filename, bytes=path.stat().st_size, work=work,
                          detection=detection, source_notes=source_notes, result=None)
    return dict(token=token, filename=upload.filename, bytes=path.stat().st_size,
                members=len(files), source_notes=source_notes, **detection)

def convert(token, slug=None):
    item = UPLOADS.get(token)
    if not item: raise ValueError('Choose the file again. This upload is no longer available in this session.')
    slug = slug or item['detection']['slug']
    if slug not in BY: raise ValueError('Choose the dataset for this file before converting.')
    # An explicit repeat returns the completed result; it never creates a duplicate run.
    if item['result'] and item['result']['slug'] == slug: return item['result']
    status, fn = route(BY[slug])
    if status in ('stub','retired'): raise ValueError('This dataset has no conversion parser. Choose a supported dataset.')
    run_id = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    out = OUT / run_id
    out.mkdir()
    try:
        counts, note = fn(item['files'], str(out))
        if item.get('source_notes'):
            note = ' '.join(filter(None, [note] + item['source_notes']))
        if not counts or sum(counts.values()) == 0:
            raise ValueError(note or 'No records were produced. Check the dataset choice and download the original RRC data file again.')
        previews = []
        for name, rows in counts.items():
            csvpath = out / (name+'.csv')
            if not csvpath.exists(): continue
            with csvpath.open(encoding='utf-8-sig', newline='') as fh:
                reader = csv.reader(fh)
                columns = next(reader, [])
                sample = []
                for i,row in enumerate(reader):
                    if i >= 5: break
                    sample.append(row)
            previews.append(dict(name=name, rows=rows, columns=columns, preview=sample))
        display_name = item['detection'].get('display_name') if slug == item['detection'].get('slug') else None
        result = dict(id=run_id, slug=slug, dataset=display_name or BY[slug]['name'], filename=item['filename'],
                      status='Files organized' if status=='wired:image-unpack' else 'Conversion complete',
                      counts=counts, records=sum(counts.values()),
                      record_unit='output rows' if any(n.startswith('ascii_') for n in counts) and any(n.startswith('ebcdic_') for n in counts) else 'records',
                      tables=previews, note=note,
                      download='/download/'+run_id, output=str(out),
                      support=BY[slug]['support'])
        (out/'conversion.json').write_text(json.dumps({k:v for k,v in result.items() if k!='tables'}, indent=2), encoding='utf-8')
        RESULTS[run_id] = out
        item['result'] = result
        return result
    except Exception:
        shutil.rmtree(out, ignore_errors=True)
        raise

@app.get('/api/catalog')
def catalog(): return jsonify(datasets=CAT)

@app.get('/api/health')
def health(): return jsonify(application='Data Train', version='1.0.0', pid=os.getpid())

@app.post('/api/detect')
def detect_api():
    try: return jsonify(stage(request.files.get('file')))
    except (ValueError, OSError) as exc: return error(str(exc))
    except Exception:
        app.logger.exception('Could not inspect input')
        return error('This file could not be inspected. Check that the download finished and choose it again.')

@app.post('/api/convert')
def convert_api():
    data = request.get_json(silent=True) or request.form
    if not LOCK.acquire(blocking=False): return error('A conversion is already running. Wait for it to finish.', 409)
    try: return jsonify(convert(data.get('token'),data.get('slug')))
    except ValueError as exc: return error(str(exc))
    except Exception:
        detail = traceback.format_exc()
        app.logger.error(detail)
        return error('Conversion could not finish. Check that this is the original RRC data file and confirm its dataset.', details=detail)
    finally: LOCK.release()

@app.get('/download/<run_id>')
def download(run_id):
    if not run_id or '/' in run_id or '\\' in run_id: abort(404)
    out = OUT / run_id
    if not out.is_dir() or not (out/'conversion.json').is_file(): abort(404)
    archive = WORK / (run_id+'.zip')
    if not archive.exists(): shutil.make_archive(str(archive.with_suffix('')), 'zip', str(out))
    return send_file(archive, as_attachment=True, download_name='RRC-results-'+run_id+'.zip')

@app.post('/api/quit')
def quit_api():
    # A loopback browser must make a same-origin request; a remote page cannot stop this app.
    origin = request.headers.get('Origin')
    if origin and origin != request.host_url.rstrip('/'): return error('Use the application window to quit.', 403)
    callback = app.config.get('RRC_SHUTDOWN')
    if callback:
        threading.Timer(.4, callback).start()
        return jsonify(message='Application closed. You can close this browser tab.')
    return error('Close the source server to quit this development session.', 409)

@app.errorhandler(RequestEntityTooLarge)
def large_file(_): return error('This file exceeds the upload limit. Choose a smaller RRC download.',413)

def cleanup(): shutil.rmtree(WORK, ignore_errors=True)
