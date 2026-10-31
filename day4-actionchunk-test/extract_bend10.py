import pathlib,tarfile,hashlib,shutil
base=pathlib.Path('day4-actionchunk-test/results').resolve(); archive=base/'day4-minimum-half-fold-20261031-070836-491946.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ced8d3109a658a33050140b6f348ffeb4d1e2cd093e7cbc805b130916c0ce265'
with tarfile.open(archive) as tar:
 for m in tar:
  dest=(base/m.name).resolve();assert base in dest.parents and (m.isfile() or m.isdir())
  if m.isdir():dest.mkdir(parents=True,exist_ok=True)
  else:
   dest.parent.mkdir(parents=True,exist_ok=True)
   with tar.extractfile(m) as src,dest.open('wb') as dst:shutil.copyfileobj(src,dst)
print('ARCHIVE_VERIFIED_EXTRACTED')
