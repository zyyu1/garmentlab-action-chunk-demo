"""Stage 6 BC evaluation adapter (does not modify Stage 4/5 frozen entry).

Run the original `stage4_success_v1.evaluate` unchanged, then separate:
  * physics  : held, released_continuously, geometry_entire_window, stable
  * protocol : task definition, no_runtime_error, budget (BC-equivalent:
               action_count within the level limit, L1<=7, L2/L3<=12)

BC acceptance = physics_ok AND definition AND no_runtime_error AND budget_ok.
Expert-only action labels / fixed sequence / release_retreat naming are not
required; no geometry threshold is reimplemented or relaxed.
"""
LEVEL_BUDGET = {'flat': 7, 'perturbed': 12, 'crumpled': 12}
PHYSICS_CHECKS = ('held', 'released_continuously', 'geometry_entire_window', 'stable')


def physical_verdict(meta, data):
    from stage4_success_v1 import evaluate
    try:
        r = evaluate(meta, data)
    except Exception as exc:
        return {'status': 'incomplete', 'error': repr(exc), 'accepted': False,
                'physics_ok': None}
    checks = r.get('checks') or {}
    physics = {k: checks.get(k) for k in PHYSICS_CHECKS}
    physics_ok = all(v is True for v in physics.values())
    level = meta.get('level')
    limit = LEVEL_BUDGET.get(level)
    n = meta.get('action_count', -1)
    definition = bool(checks.get('definition'))
    no_error = meta.get('errors') == []
    budget_ok = isinstance(n, int) and 0 < n <= limit if limit else False
    accepted = bool(physics_ok and definition and no_error and budget_ok)
    return {
        'status': r.get('status'), 'success': r.get('success'),
        'physics_ok': bool(physics_ok), 'physics': physics,
        'definition': definition, 'no_runtime_error': no_error,
        'budget_ok': bool(budget_ok), 'budget_limit': limit, 'action_count_actual': int(n),
        'accepted': accepted,
        'expert_budget_exact': checks.get('budget'),
        'stability': r.get('stability'),
        'failed_geometry_frames': r.get('failed_geometry_frames'),
    }
