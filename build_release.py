"""Build a Windows folder/ZIP from this source tree using a provisioned build Python.

Build only. End users run the produced executable and need no Python or Node install.
Usage: python build_release.py --node-dir <official extracted node folder> --output <folder>
"""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--node-dir', required=True, type=Path)
    args.add_argument('--output', required=True, type=Path)
    args.add_argument('--skip-archives', action='store_true', help='Build an integration candidate folder without release ZIPs.')
    options = args.parse_args()
    node = options.node_dir.resolve()
    if not (node/'node.exe').is_file() or not (node/'LICENSE').is_file():
        raise SystemExit('Use the complete official Node Windows archive (node.exe and LICENSE).')
    output = options.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    build = output/'build'
    stage = build/'bundle-data'
    stage.mkdir(parents=True,exist_ok=True)
    runtime = stage/'runtime'; runtime.mkdir(exist_ok=True)
    shutil.copy2(node/'node.exe',runtime/'node.exe')
    shutil.copy2(node/'LICENSE',runtime/'NODE-LICENSE.txt')
    app = ROOT/'rrc-drop-runner'
    command = [sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
               '--name','Data Train','--distpath',str(output/'dist'),
               '--workpath',str(build/'pyinstaller'),'--specpath',str(build),
               '--paths',str(app),'--paths',str(ROOT/'TXRRC_data_harvest'),
               '--hidden-import','api_compressed','--hidden-import','pending_permits',
               '--hidden-import','layouts_p5','--hidden-import','ebcdic_main',
               '--hidden-import','ebcdic_formats','--hidden-import','layouts_wells_dbf900']
    data = [(ROOT/'datasets-catalog.json','.'),(app/'layouts','rrc-drop-runner/layouts'),
            (app/'layout_completions.json','rrc-drop-runner'),
            (app/'templates','rrc-drop-runner/templates'),(app/'static','rrc-drop-runner/static'),
            (ROOT/'w1-data-parser/dist','w1-data-parser/dist'),
            (ROOT/'w1-data-parser/package.json','w1-data-parser'),
            (runtime,'runtime')]
    for filename in ['ebcdic_formats.py','ebcdic_main.py','layouts_wells_dbf900.py','LICENSE']:
        data.append((ROOT/'TXRRC_data_harvest'/filename,'TXRRC_data_harvest'))
    for source,destination in data:
        command += ['--add-data',str(source)+';'+destination]
    command.append(str(app/'launcher.py'))
    subprocess.run(command,cwd=ROOT,check=True)
    folder = output/'dist'/'Data Train'
    for name in ['READ ME FIRST.txt','LICENSE','ATTRIBUTION.md','THIRD-PARTY-NOTICES.txt']:
        shutil.copy2(ROOT/name,folder/name)
    notices = folder/'Licenses'; notices.mkdir(exist_ok=True)
    shutil.copy2(node/'LICENSE',notices/'Node.js.txt')
    shutil.copy2(ROOT/'TXRRC_data_harvest/LICENSE',notices/'TXRRC_data_harvest.txt')
    shutil.copy2(ROOT/'W1-ISC-NOTICE.txt',notices/'W1-ISC-NOTICE.txt')
    icon_license = app/'static/icons/LICENSE'
    if icon_license.exists(): shutil.copy2(icon_license,notices/'Bootstrap-Icons.txt')
    font_license = app/'static/fonts/OFL-Playfair-Display.txt'
    if font_license.exists(): shutil.copy2(font_license,notices/'Playfair-Display-OFL.txt')
    material_notice = app/'static/materials/NOTICE.md'
    if material_notice.exists(): shutil.copy2(material_notice,notices/'Material-Assets.md')
    python_license = Path(sys.base_prefix)/'LICENSE.txt'
    if not python_license.exists(): raise SystemExit('Python runtime license is missing.')
    shutil.copy2(python_license,notices/'Python.txt')
    runtime_packages = ['Flask','pandas','pyshp','waitress','numpy','python-dateutil','tzdata',
                        'blinker','click','itsdangerous','jinja2','markupsafe','werkzeug','six',
                        'pyinstaller','pyinstaller-hooks-contrib']
    versions = {}
    for name in runtime_packages:
        dist = metadata.distribution(name)
        versions[name] = dist.version
        target = notices/name
        target.mkdir(exist_ok=True)
        for file in dist.files or []:
            text = str(file)
            base = Path(text).name.lower()
            if '.dist-info' in text and (base in ('metadata','license','license.txt','license.md','copying','copying.txt','notice','notice.txt') or '/licenses/' in text.replace('\\','/')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    relative = text.replace('\\','/').split('.dist-info/',1)[-1]
                    destination = target/relative
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,destination)
    import PyInstaller
    pyinstaller_license = Path(PyInstaller.__file__).parent/'COPYING.txt'
    if pyinstaller_license.exists(): shutil.copy2(pyinstaller_license,notices/'PyInstaller-COPYING.txt')
    versions.update(python=sys.version, node=subprocess.check_output([str(node/'node.exe'),'--version'],text=True).strip())
    (folder/'build-versions.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
    if options.skip_archives:
        print(json.dumps(dict(candidate_folder=str(folder)),indent=2))
        return
    archive=output/'Data-Train-1.0.0-Windows-x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in folder.rglob('*'):
            if path.is_file(): z.write(path,str(path.relative_to(folder.parent)))
    source_archive=output/'Data-Train-1.0.0-Source.zip'
    with zipfile.ZipFile(source_archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in ROOT.rglob('*'):
            if path.is_file() and path.name != 'design-qa.md' and not any(p in ('__pycache__','.git','out','samples','.venv') for p in path.relative_to(ROOT).parts):
                z.write(path,str(Path('Data-Train-Source')/path.relative_to(ROOT)))
    print(json.dumps(dict(windows_zip=str(archive),source_zip=str(source_archive)),indent=2))

if __name__=='__main__': main()
