"""Single-writer append-only attempt journal. No formal classification logic."""
import json
from pathlib import Path

TERMINAL={'success','rejected','error'}
REQUIRED={'attempt_id','seed','difficulty','status','versions','attempted_actions',
          'completed_actions','recovery_attempts','success','failure_reason','artifacts'}

def read(path):
    p=Path(path)
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []

def append(path,row):
    if not REQUIRED<=row.keys():raise ValueError('Missing attempt fields')
    if not isinstance(row['attempt_id'],str) or not row['attempt_id']:raise ValueError('Invalid attempt id')
    if type(row['seed']) is not int or row['difficulty'] not in ('flat','perturbed','crumpled'):raise ValueError('Invalid seed/difficulty')
    status=row['status']
    if status not in TERMINAL|{'running'}:raise ValueError('Invalid status')
    for k in ('attempted_actions','completed_actions','recovery_attempts'):
        if type(row[k]) is not int or row[k]<0:raise ValueError('Invalid counters')
    if row['completed_actions']>row['attempted_actions']:raise ValueError('Completed exceeds attempted')
    if status=='success':
        if row['success'] is not True or row['attempted_actions']>12 or row['recovery_attempts']>2:
            raise ValueError('Invalid successful attempt')
        if not row.get('evaluation_frozen') or not row.get('metrics') or not row['versions'].get('evaluator'):
            raise ValueError('Success needs frozen evaluator and metrics')
    elif status=='running':
        if row['success'] is not None:raise ValueError('Running success must be null')
    elif row['success'] is not False or not row['failure_reason']:raise ValueError('Failure needs reason')
    if not row['versions'] or not isinstance(row['artifacts'],dict):raise ValueError('Missing provenance')
    prior=[x for x in read(path) if x['attempt_id']==row['attempt_id']]
    if prior:
        old=prior[-1]
        if old['status'] in TERMINAL:raise ValueError('Terminal attempt is immutable; retry uses new id')
        if any(old[k]!=row[k] for k in ('seed','difficulty','versions')):raise ValueError('Attempt identity changed')
        if any(row[k]<old[k] for k in ('attempted_actions','completed_actions','recovery_attempts')):
            raise ValueError('Counters decreased')
    elif status!='running':raise ValueError('Record running before terminal result')
    encoded=json.dumps(row,allow_nan=False,ensure_ascii=False)
    with Path(path).open('a',encoding='utf-8') as f:f.write(encoded+'\n')

def summarize(path):
    latest={r['attempt_id']:r for r in read(path)}
    out={}
    for level in ('flat','perturbed','crumpled'):
        rows=[r for r in latest.values() if r['difficulty']==level]
        counts={s:sum(r['status']==s for r in rows) for s in TERMINAL|{'running'}}
        out[level]={'total_attempts':len(rows),**counts,
                    'rejection_rate':((counts['rejected']+counts['error'])/len(rows)
                                      if rows and not counts['running'] else None)}
    return out
