"""Build the minimum acceptance report/package from the remote state."""
import csv
import hashlib
import json
from pathlib import Path

STATE = Path('/root/autodl-tmp/stage4-minimum-hold120-state-v1')
OUT = Path('/root/autodl-tmp/stage4-minimum-hold120-report')
OUT.mkdir(exist_ok=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


records = [json.loads(l) for l in (STATE / 'attempts.jsonl').read_text().splitlines() if l.strip()]
summary = json.loads((STATE / 'summary.json').read_text())
shots = json.loads((STATE / 'screenshots.json').read_text())
levels = summary['levels']
with (OUT / 'cases.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['slot', 'seed', 'level', 'mode', 'state', 'quality', 'entry_exit', 'runner_exit',
                'audit_exit', 'file_complete', 'observation_semantics_valid', 'overall_valid',
                'hold_applicable', 'recovery_hold', 'result_dir'])
    for r in records:
        w.writerow([r.get('slot'), r.get('seed'), r.get('level'), r.get('mode'), r.get('state'),
                    r.get('quality_status'), r.get('entry_exit'), r.get('runner_exit'),
                    r.get('audit_exit'), r.get('file_complete'), r.get('observation_semantics_valid'),
                    r.get('overall_valid'), r.get('hold_applicable'), r.get('recovery_hold'),
                    r.get('result_dir')])
report = {'summary': summary, 'screenshots': len(shots),
          'screenshots_by_level': {k: sum(1 for v in shots.values() if v['level'] == k)
                                   for k in ('flat', 'perturbed', 'crumpled')},
          'records': len(records),
          'note': 'Minimum acceptance: per level stop at 5 valid successes; not a fixed-sample success rate.'}
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
