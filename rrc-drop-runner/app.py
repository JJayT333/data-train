from pathlib import Path
from flask import request, render_template, render_template_string
from parsers import ROOT, route
from service import app, CAT, BY, stage, convert
PAGE = """<!doctype html><title>Data Train</title><style>body{font-family:sans-serif;max-width:800px;margin:2em auto}
#drop{border:3px dashed #888;padding:3em;text-align:center}#drop.on{background:#eef}td,th{padding:4px 8px;border-bottom:1px solid #ddd}</style>
<h1>Data Train</h1><p>1. Drop your Texas RRC download &nbsp; 2. Pick what it is &nbsp; 3. Click Run</p><form method=post enctype=multipart/form-data>
<div id=drop>Drop an RRC download here or <input type=file name=file id=f required></div><p>
<select name=slug required><option value="">â€” pick dataset â€”</option>
{% for d in cat %}<option value="{{d.slug}}" {{'selected' if d.slug==sel}}>[{{st[d.slug]}}] {{d.name}} ({{d.formats|join(', ')}})</option>{% endfor %}</select>
<button>Run</button> <small>Zip files are fine; we unpack them.</small></form>
<script>const d=drop,f=document.getElementById('f');['dragover','dragenter'].forEach(e=>d.addEventListener(e,x=>{x.preventDefault();d.classList.add('on')}));
d.addEventListener('dragleave',()=>d.classList.remove('on'));d.addEventListener('drop',x=>{x.preventDefault();f.files=x.dataTransfer.files;d.classList.remove('on');d.firstChild.textContent=f.files[0].name+' ';});</script>
{% if res %}<h2>{{res.status}}</h2><p>Output: <code>{{res.out}}</code></p>{% if res.note %}<p><i>{{res.note}}</i></p>{% endif %}
{% if res.zip %}<p><a href="/download/{{res.zip}}"><b>&#11015; Download results as zip</b></a></p>{% endif %}{% if res.err %}<pre>{{res.err}}</pre>{% endif %}<table><tr><th>Table</th><th>Rows</th></tr>{% for k,v in res.counts.items() %}<tr><td>{{k}}</td><td>{{v}}</td></tr>{% endfor %}</table>{% endif %}"""
ST = {d['slug']: d['support'] for d in CAT}

@app.route('/', methods=['GET', 'POST'])
def index():
    template = Path(ROOT) / 'templates' / 'index.html'
    if template.exists(): return render_template('index.html', cat=CAT)
    res = None
    sel = request.form.get('slug')
    if request.method == 'POST':
        try:
            staged = stage(request.files.get('file'))
            result = convert(staged['token'], sel)
            res = dict(status=result['status'], out=result['output'], counts=result['counts'], note=result['note'], err=None, zip=result['id'])
        except Exception as exc:
            res = dict(status='Could not convert', out='', counts={}, note=str(exc), err=None, zip=None)
    return render_template_string(PAGE, cat=CAT, st=ST, sel=sel, res=res)

if __name__ == '__main__':
    from launcher import main
    main()
