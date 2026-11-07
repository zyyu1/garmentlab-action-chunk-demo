from pathlib import Path

p = Path('collect_demos.py')
s = p.read_text(encoding='utf-8')
anchor = '    # -- main ---------------------------------------------------------\n'
assert anchor in s, 'anchor missing'
method = '''    def _verify_export(self, rec):
        """Full demo gate: per-episode obs + action alignment + single/H4 export."""
        obs = self._valid_obs(rec)
        if not obs:
            return None
        rd = rec.get('result_dir')
        out = self.state / 'exports' / ('%s-%s' % (rec.get('level'), rec.get('seed')))
        cmd = [self.python, str(HERE / 'verify_export.py'), '--run-dir', str(rd),
               '--obs-dir', obs['obs_dir'], '--phase-map', str(HERE / 'phase_map.json'),
               '--out', str(out)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            return None
        try:
            s = json.loads((out / 'export_summary.json').read_text(encoding='utf-8'))
        except Exception:
            return None
        c = s.get('checks') or {}
        ok = (bool(c.get('count_match')) and bool(c.get('pairing_ok'))
              and bool(c.get('quat_shape_ok')) and bool(c.get('quat_unit_norm'))
              and s.get('verdict_status') == 'accepted'
              and (s.get('single_step') or {}).get('count') == obs['action_count']
              and bool((s.get('h4') or {}).get('no_cross_episode')))
        if not ok:
            return None
        return {'obs_dir': obs['obs_dir'], 'export_dir': str(out),
                'obs_count': obs['obs_count'], 'action_count': obs['action_count'],
                'single_step': s['single_step']['count'], 'h4_chunks': s['h4']['total_chunks']}

'''
s = s.replace(anchor, method + anchor)

old1 = "            accepted = [r['seed'] for r in done\n                        if r.get('state') == 'accepted' and self._valid_obs(r)]"
new1 = "            accepted = [r['seed'] for r in done\n                        if r.get('state') == 'accepted' and self._verify_export(r)]"
assert old1 in s, 'accepted line not found'
s = s.replace(old1, new1)

old2 = "                    valid = self._valid_obs(rec)"
new2 = "                    valid = self._verify_export(rec)"
assert old2 in s, 'accept branch not found'
s = s.replace(old2, new2)

p.write_text(s, encoding='utf-8')
print('export_gate_added')
