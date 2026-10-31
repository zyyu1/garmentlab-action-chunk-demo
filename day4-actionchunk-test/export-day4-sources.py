"""Read-only source handoff for Day4 implementation. Standard library; no Isaac import."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path('/root/autodl-tmp')
REPOS = {'demo': ROOT/'garmentlab-action-chunk-demo',
         'garmentlab': ROOT/'garmentlab_workspace/GarmentLab'}
EXCLUDED = {'.git','__pycache__','.venv','venv','node_modules','assets','results',
            'outputs','checkpoints','wandb','.ssh','.aws','.azure'}
SUFFIXES = {'.py','.yaml','.yml','.md','.toml','.ini','.cfg','.sh'}


def collect(root, label, archive):
    root = Path(root).resolve()
    manifest = {}
    skipped = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED
                         and not (Path(current)/d).is_symlink())
        for name in sorted(files):
            path = Path(current)/name
            if path.is_symlink() or (path.suffix.lower() not in SUFFIXES and name not in ('requirements.txt','CMakeLists.txt')):
                continue
            if any(word in name.lower() for word in ('secret','credential','token','password')):
                skipped.append(str(path.relative_to(root)))
                continue
            if path.stat().st_size > 5*1024*1024:
                skipped.append(str(path.relative_to(root)))
                continue
            data = path.read_bytes()
            relative = label+'/'+path.relative_to(root).as_posix()
            archive.writestr(relative, data)
            manifest[relative] = {'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data)}
    return manifest, skipped


def git_info(root):
    info = {}
    for key,args in [('head',['rev-parse','HEAD']),('status',['status','--short','--branch'])]:
        p = subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,timeout=30)
        info[key] = {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    return info


def main():
    for root in REPOS.values():
        if not root.is_dir():
            raise RuntimeError('Missing repository: '+str(root))
    output = ROOT/('day4-source-handoff-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
    manifest = {}
    metadata = {'scope':'source/config snapshot only; no environment or physics execution', 'repositories':{}}
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for label,root in REPOS.items():
            entries,skipped=collect(root,label,archive)
            if not entries:
                raise RuntimeError('No source files collected: '+label)
            manifest.update(entries)
            metadata['repositories'][label]={'path':str(root),'git':git_info(root),'skipped':skipped}
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        archive.writestr('metadata.json',json.dumps(metadata,indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity failure')
        for name,item in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=item['sha256']:
                raise RuntimeError('Content hash mismatch: '+name)
    print('DAY4_SOURCE_HANDOFF_OK',len(manifest),'files',flush=True)
    print('DOWNLOAD_FILE',output,flush=True)


if __name__=='__main__':
    main()
