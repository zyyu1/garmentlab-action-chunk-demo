from pathlib import Path
b=Path('day4-actionchunk-test');s=(b/'day4-attachment-canary.py').read_text()
s=s.replace("result = {'case': args.case,", "result = {'probe_version': 'attachment-canary-mass-v2', 'case': args.case,")
s=s.replace("    def record(step):",'''    particle_masses = None
    if cloth is not None:
        result['cloth_mass_readbacks'] = {}
        result['cloth_authored_total_mass_kg'] = float(UsdPhysics.MassAPI(mesh.GetPrim()).GetMassAttr().Get())
    def capture_mass(step):
        masses = array(cloth.get_masses()).reshape(-1)
        if masses.shape != (len(points),) or not np.isfinite(masses).all() or not (masses > 0).all():
            raise RuntimeError('Invalid runtime cloth particle masses')
        result['cloth_mass_readbacks'][str(step)] = {
            'particle_masses_kg': masses.tolist(), 'total_kg': float(masses.sum()),
            'min_kg': float(masses.min()), 'max_kg': float(masses.max()),
            'matches_authored_total_rtol_0_002': bool(np.isclose(masses.sum(), .021, rtol=.002, atol=0)),
            'unchanged_from_start': particle_masses is None or bool(np.array_equal(masses, particle_masses))}
        return masses
    if cloth is not None:
        particle_masses = capture_mass(0)
    def record(step):''')
s=s.replace("            desired = rot.apply(points[ids]-[0,0,1])+t[:3]",'''            if step in (120, 180):
                capture_mass(step)
            center = np.average(v, axis=0, weights=particle_masses)
            # External gravity moment of the entire cloth, NOT attachment reaction torque.
            gravity_moment = np.cross(v-[0,0,1], particle_masses[:,None]*np.array([0.,0.,-9.81])).sum(axis=0)
            row.update(cloth_mass_centroid_m=center.tolist(),
                       cloth_gravity_moment_about_pivot_Nm=gravity_moment.tolist())
            desired = rot.apply(points[ids]-[0,0,1])+t[:3]''')
(b/'day4-attachment-canary-v2.py').write_text(s,encoding='utf8')
s=(b/'evaluate-attachment-canary.py').read_text().replace("'valid_no_detected_attachment_reaction'", "'valid_response_below_preregistered_threshold'")
s=s.replace("checks = {name: bool(value) for name, value in checks.items()}",'''if case != 'rigid':
    reads = r.get('cloth_mass_readbacks', {})
    mass_valid = set(reads) == {'0', '120', '180'} and all(
        x['matches_authored_total_rtol_0_002'] and x['unchanged_from_start'] for x in reads.values())
    checks['runtime_cloth_mass_matches_authored_and_stable'] = mass_valid
    if not mass_valid:
        diagnosis = 'mass_configuration_mismatch_or_recording_failed'
checks = {name: bool(value) for name, value in checks.items()}''')
(b/'evaluate-attachment-canary-v2.py').write_text(s,encoding='utf8')
s=(b/'run-attachment-canary.sh').read_text().replace('attachment-canary-files.json','attachment-canary-v2-files.json').replace('day4-attachment-canary.py','day4-attachment-canary-v2.py').replace('evaluate-attachment-canary.py','evaluate-attachment-canary-v2.py').replace('run-attachment-canary.sh','run-attachment-canary-v2.sh').replace('day4-attachment-canary-XXXXXXXX','day4-attachment-canary-v2-XXXXXXXX')
(b/'run-attachment-canary-v2.sh').write_text(s,encoding='utf8')
print('V2_MEASUREMENT_ONLY_FILES_WRITTEN')
