"""Offline E summary, based on durable D journal and candidate verdicts."""
import argparse
from pathlib import Path
from collections import Counter
import json
from stage4_batch_preflight import journal

def summarize(state, results, pinned):
    table = {level: Counter() for level in ('flat','perturbed','crumpled')}
    rows = []
    for row in journal(state/'attempts.jsonl'):
        label = 'error'
        path = results/Path(row.get('result_dir') or 'missing-result').name
        if row.get('event') == 'finished' and row.get('result_dir') and (path/'a5-verdict.json').is_file():
            v=json.loads((path/'a5-verdict.json').read_text())
            if (v['split'],v['level'],v['seed'],v['mode'],v['manifest_sha256']) != ('formal',row['level'],row['seed'],row['execution'],pinned):
                raise ValueError('Formal verdict/attempt identity mismatch')
            if (row['exit_code'],v['status']) in ((0,'accepted'),(1,'rejected')):
                label=v['status']
        table[row['level']][label]+=1
        rows.append(dict(seed=row['seed'],level=row['level'],mode=row['execution'],status=label))
    return {'rows':rows,'levels':{k:dict(attempts=sum(v.values()),accepted=v['accepted'],rejected=v['rejected'],
            error=v['error'],rejection_rate=(v['rejected']+v['error'])/sum(v.values()) if v else None) for k,v in table.items()}}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('state',type=Path);ap.add_argument('results',type=Path);ap.add_argument('release',type=Path);a=ap.parse_args()
    print(json.dumps(summarize(a.state,a.results,json.loads(a.release.read_text())['manifest_sha256']),indent=2))
