"""Compare the zerovel arc135 window against the original deep diagnostic.

Reads two JSONL logs (one record per line) and prints a markdown summary.
No simulation access; pure offline analysis.
"""
import json
import sys
from pathlib import Path


def load(path):
    recs = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            recs.append(json.loads(line))
    return recs


def window_ticks(recs):
    return [r for r in recs if r.get('kind') == 'window_tick']


def longest_true(flags):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def summarize(ticks):
    out = {'ticks': len(ticks)}
    if not ticks:
        return out
    vels = []
    for t in ticks:
        v = (t.get('after') or {}).get('joint_velocities')
        if v:
            vels.append(max(abs(x) for x in v[:7]))
    errs = [t['error_m'] for t in ticks if t.get('error_m') is not None]
    flags = [bool(t.get('all_ok')) for t in ticks]
    out.update({
        'max_abs_joint_velocity_rad_s': max(vels) if vels else None,
        'velocity_p95_rad_s': sorted(vels)[int(0.95 * (len(vels) - 1))] if vels else None,
        'ee_error_first_m': errs[0] if errs else None,
        'ee_error_min_m': min(errs) if errs else None,
        'ee_error_last_m': errs[-1] if errs else None,
        'ticks_with_all_ok': sum(flags),
        'longest_consecutive_ok': longest_true(flags),
        'first_ok_tick': next((t['tick'] for t in ticks if t.get('all_ok')), None),
        'converged': any(r.get('kind') == 'converged' for r in []),  # filled by caller
    })
    return out


def main(path_zerovel, path_deep, out_json):
    z = load(path_zerovel)
    d = load(path_deep)
    zt, dt = window_ticks(z), window_ticks(d)
    zs, ds = summarize(zt), summarize(dt)
    zs['converged'] = any(r.get('kind') == 'converged' for r in z)
    zs['timeout'] = any(r.get('kind') == 'timeout' for r in z)
    ds['converged'] = any(r.get('kind') == 'converged' for r in d)
    ds['timeout'] = any(r.get('kind') == 'timeout' for r in d)

    readback = [r for r in z if r.get('kind') == 'zerovel_readback']
    err = [r for r in z if r.get('kind') == 'zerovel_readback_error']
    rb = readback[0] if readback else None

    # the original RMP output for the same (first) window tick
    rmp_first = next((r for r in z if r.get('kind') == 'rmp_output'
                      and (r.get('context') or {}).get('phase') == 'window'
                      and (r.get('context') or {}).get('tick') == 0), None)
    rmp_pos = rmp_first['rmp_action']['joint_positions'] if rmp_first else None
    rmp_vel = rmp_first['rmp_action']['joint_velocities'] if rmp_first else None
    drive_vs_rmp = None
    if rb and rmp_pos:
        drive_vs_rmp = max(abs(a - b) for a, b in zip(rb['drive_positions'], rmp_pos))

    result = {
        'zerovel': zs,
        'original_deep': ds,
        'readback': {
            'present': rb is not None,
            'error': err[0]['error'] if err else None,
            'sent_velocities': rb['sent_velocities'] if rb else None,
            'drive_velocities': rb['drive_velocities'] if rb else None,
            'pos_max_abs_diff_sent_vs_drive': rb['pos_max_abs_diff'] if rb else None,
            'pos_max_abs_diff_rmp_vs_drive': drive_vs_rmp,
            'vel_max_abs': rb['vel_max_abs'] if rb else None,
            'vel_zero_exact': rb['vel_zero_exact'] if rb else None,
        },
        'rmp_window_tick0_positions': rmp_pos,
        'rmp_window_tick0_velocities': rmp_vel,
        'per_tick': {
            'zerovel': [(t['tick'], round(t['error_m'] * 1000, 3),
                         round(max(abs(x) for x in (t['after'].get('joint_velocities') or [0])[:7]), 4),
                         t.get('all_ok'), t.get('consecutive')) for t in zt],
        },
    }
    Path(out_json).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('zerovel', 'original_deep', 'readback')}, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
