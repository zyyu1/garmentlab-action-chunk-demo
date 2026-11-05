"""Offline batch validation and durable journal; never imports a simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

RANGES = {'flat': range(4110, 4130), 'perturbed': range(4210, 4230),
          'crumpled': range(4310, 4330)}
MODES = ('single', 'arc4')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(seeds_path, plan_path):
    seeds, plan = read(seeds_path), read(plan_path)
    rows = seeds['heldout']
    expected = {(level, seed) for level, group in RANGES.items() for seed in group}
    actual = [(r['level'], r['seed']) for r in rows]
    if len(actual) != 60 or set(actual) != expected:
        raise ValueError('heldout must contain exactly the registered 60 unique seeds')
    dev = {s for group in seeds['dev_seeds'].values() for s in group}
    if dev != set(range(4100, 4110)) | set(range(4200, 4210)) | set(range(4300, 4310)):
        raise ValueError('development seed registration changed')
    entries = plan['episodes']
    by_seed = {r['seed']: r for r in entries}
    if len(by_seed) != len(entries):
        raise ValueError('duplicate seed in initial plan')
    for row in rows:
        if by_seed.get(row['seed']) != row:
            raise ValueError('full initial plan mismatch: ' + str(row['seed']))
    return {'heldout_seeds': 60, 'planned_fold_attempts': 120,
            'seed_sha256': sha(seeds_path), 'plan_sha256': sha(plan_path),
            'simulation_started': False}


def journal(path):
    """Collapse start/end events; unfinished starts remain denominator errors."""
    records, positions = [], {}
    if not Path(path).exists():
        return records
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)  # damaged journals fail closed, never truncate
        aid = rec.get('attempt_id')
        if not aid:
            records.append(rec)  # legacy terminal rows remain supported
            continue
        event = rec.get('event')
        if event == 'started':
            if aid in positions:
                raise ValueError('duplicate attempt start: ' + aid)
            positions[aid] = len(records)
            records.append(rec)
        elif event == 'finished':
            if aid not in positions:
                raise ValueError('finish without start: ' + aid)
            old = records[positions[aid]]
            if old.get('event') != 'started' or any(old[k] != rec[k] for k in
                    ('level', 'seed', 'execution', 'initial_dir')):
                raise ValueError('conflicting finish: ' + aid)
            records[positions[aid]] = rec
        else:
            raise ValueError('unknown journal event at line ' + str(number))
    return records


def append(path, row):
    with Path(path).open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(row) + '\n')
        fh.flush()
        os.fsync(fh.fileno())


BASE = Path(__file__).resolve().parent
PROTOCOL_VERSION = 'stage4-initial-v2-task-scoped'
INITIAL_SPEC = {
    'flat': (0.0, 'A_l1_overfold', 'day4-square-initial.py', 'square-initial-files.json'),
    'perturbed': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                  'square-initial-stripfold-files.json'),
    'crumpled': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                 'square-initial-stripfold-files.json'),
}


def initial(path, level, seed):
    path = Path(path)
    result = read(path / 'result.json')
    case = result.get('initial_case', {})
    if result.get('passed') is not True or (case.get('level'), case.get('seed')) != (level, seed):
        raise ValueError('initial result identity/gate mismatch: ' + str(path))
    for name in ('initial_geometry.npz', 'initial.png'):
        if not (path / name).is_file():
            raise ValueError('initial artifact missing: ' + str(path / name))
    expected_scale, expected_task, script, files_json = INITIAL_SPEC[level]
    proto = result.get('protocol') or {}
    if proto.get('version') != PROTOCOL_VERSION:
        raise ValueError('old or unregistered initial protocol rejected: ' + str(path))
    if (proto.get('task'), proto.get('level'), proto.get('seed')) != (expected_task, level, seed):
        raise ValueError('initial protocol identity mismatch: ' + str(path))
    for key in ('particle_friction_scale_expected', 'particle_friction_scale_readback'):
        value = proto.get(key)
        if not isinstance(value, (int, float)) or abs(float(value) - expected_scale) > 1e-6:
            raise ValueError('initial protocol %s mismatch for %s: %r'
                             % (key, level, value))
    binding = proto.get('material_binding') or {}
    if binding.get('particle_material') != '/World/Garment/particleMaterial' \
            or not binding.get('particle_system'):
        raise ValueError('initial material binding missing/mismatch: ' + str(path))
    gen = proto.get('generator') or {}
    if gen.get('script') != script or gen.get('script_sha256') != sha(BASE / script):
        raise ValueError('initial generator identity mismatch: ' + str(path))
    if gen.get('files_manifest') != files_json or \
            gen.get('files_manifest_sha256') != sha(BASE / files_json):
        raise ValueError('initial generator manifest mismatch: ' + str(path))
    return {name: sha(path / name) for name in ('result.json', 'initial_geometry.npz', 'initial.png')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'bind', 'status', 'start', 'finish', 'initial'])
    ap.add_argument('--seeds', default='stage4-heldout-seeds.json')
    ap.add_argument('--plan', default='square-initial-plan.json')
    ap.add_argument('--state')
    ap.add_argument('--level'); ap.add_argument('--seed', type=int)
    ap.add_argument('--execution', choices=MODES)
    ap.add_argument('--initial-dir'); ap.add_argument('--result-dir', default='')
    ap.add_argument('--exit-code', type=int)
    args = ap.parse_args()
    if args.command in ('check', 'bind'):
        report = validate(args.seeds, args.plan)
        if args.command == 'bind':
            base = Path(args.seeds).resolve().parent
            files = list(base.glob('*files.json')) + [base / name for name in
                ('run-stage4-formal-batch.sh', 'stage4_batch_preflight.py')]
            report['a5_manifest_sha256'] = sha(base / 'a5-manifest.json')
            report['a5_release_sha256'] = sha(base / 'E_RELEASE.json')
            report['infrastructure_and_manifests'] = {p.name: sha(p) for p in sorted(files)}
            state = Path(args.state); state.mkdir(parents=True, exist_ok=True)
            binding = state / 'batch-identity.json'
            if binding.exists():
                if read(binding) != report:
                    raise ValueError('batch identity changed; cannot resume')
            else:
                if (state / 'attempts.jsonl').exists() or (state / 'init_dirs.txt').exists():
                    raise ValueError('legacy state requires explicit offline migration; use no new tag to hide attempts')
                with binding.open('x', encoding='utf-8') as fh:
                    json.dump(report, fh, indent=2)
        print(json.dumps(report)); return
    state = Path(args.state)
    if args.command == 'initial':
        hashes = initial(args.initial_dir, args.level, args.seed)
        p = state / ('initial-' + str(args.seed) + '-identity.json')
        if p.exists():
            if read(p) != hashes:
                raise ValueError('reused initial changed')
        else:
            with p.open('x', encoding='utf-8') as fh:
                json.dump(hashes, fh)
        return
    log = state / 'attempts.jsonl'
    records = journal(log)
    key = (args.level, args.seed, args.execution)
    matching = [r for r in records if (r['level'], r['seed'], r['execution']) == key]
    if args.command == 'status':
        if not matching:
            print('pending'); return
        if any(r.get('event') == 'started' or not r.get('result_dir') or
               not (Path(r['result_dir']) / 'result.json').exists() for r in matching):
            raise ValueError('incomplete attempt retained; reconcile before resuming: ' + str(key))
        for r in matching:
            result_file = Path(r['result_dir']) / 'result.json'
            result = read(result_file)
            case = result.get('initial_case', {})
            if (case.get('level'), case.get('seed'), result.get('execution_mode')) != key:
                raise ValueError('recorded result identity mismatch')
            if r.get('result_sha256') != sha(result_file):
                raise ValueError('recorded result changed or lacks a bound hash')
        print('done'); return
    row = dict(level=args.level, seed=args.seed, execution=args.execution,
               initial_dir=args.initial_dir, result_dir=args.result_dir,
               exit_code=args.exit_code, attempted_utc=datetime.now(timezone.utc).isoformat())
    row['attempt_id'] = f'{args.level}-{args.seed}-{args.execution}'
    if args.command == 'start':
        if matching:
            raise ValueError('attempt already registered; never silently retry')
        row['event'] = 'started'
    else:
        if len(matching) != 1 or matching[0].get('event') != 'started':
            raise ValueError('finish requires one unfinished start')
        if matching[0]['initial_dir'] != args.initial_dir:
            raise ValueError('initial identity changed during attempt')
        row['event'] = 'finished'
        result_file = Path(args.result_dir) / 'result.json'
        if args.result_dir and result_file.is_file():
            row['result_sha256'] = sha(result_file)
    append(log, row)


if __name__ == '__main__':
    main()
