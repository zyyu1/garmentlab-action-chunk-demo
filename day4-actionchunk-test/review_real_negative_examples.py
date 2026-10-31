"""Reproducible offline review. Never enters examples into formal attempts."""
from pathlib import Path
import hashlib
import json
import numpy as np
from day4_evaluation import metrics

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'

def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def evaluate(directory, initial_file, final_file, key, yaw, label):
    p=RESULTS/directory
    initial=np.load(p/initial_file)[key]
    final=np.load(p/final_file)[key]
    local=np.load(p/'cloth_constructed.npz')['points']
    # Material IDs are fixed by the authored mesh, never reclassified at the end.
    mask=local[:,1]<-1e-6
    origin=initial[:,:2].mean(axis=0)
    normal=np.array([-np.sin(yaw),np.cos(yaw)])
    m=metrics(initial,final,mask,origin,normal)
    return {'label':label,'directory':directory,'initial_file':initial_file,'final_file':final_file,
            'source_count':int(mask.sum()),'line_origin_xy':origin.tolist(),
            'line_normal_xy':normal.tolist(),'metrics':m,
            'files_sha256':{n:checksum(p/n) for n in {initial_file,final_file,'cloth_constructed.npz'}},
            'known_label':'not_a_successful_fold','label_source':'initial-only or failed grasp-only run; no fold commanded'}

def main():
    rows=[]
    batch=json.loads((RESULTS/'L1_INITIAL_BATCH_REVIEW/summary.json').read_text())
    for r in batch['rows']:
        rows.append(evaluate(r['directory'],'initial_geometry.npz','initial_geometry.npz',
                             'settled',r['yaw_rad'],f"flat_seed_{r['seed']}"))
    d='day4-square-grasp-pose-20261031-091703-655195'
    for name,label in [('03_held.npz','held_before_release'),('04_released.npz','after_release_and_30_steps')]:
        rows.append(evaluate(d,'00_initial.npz',name,'vertices',0.,label))
    # These are characterization assertions, not proposed production thresholds.
    assert len(rows)==12
    assert all(r['metrics']['success'] is None for r in rows)
    assert all(r['metrics']['reflected_material_error_m']>.1 for r in rows)
    out=RESULTS/'REAL_NEGATIVE_EVALUATION';out.mkdir(exist_ok=True)
    report={'evaluation_status':'development_unfrozen','evaluator_sha256':checksum(ROOT/'day4_evaluation.py'),
            'count':len(rows),'rows':rows,'formal_attempts_added':0,
            'limits':'No real positive folds; no estimated classifier accuracy or frozen thresholds. Centerline numerical tolerance 1um.'}
    (out/'metrics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lines=['# Real negative examples — development metrics','',
           '| Example | Alignment mm | Particle IoU | Reflection error mm | Fixed-half drift mm |',
           '|---|---:|---:|---:|---:|']
    for r in rows:
        m=r['metrics'];lines.append(f"| {r['label']} | {1000*m['symmetric_alignment_m']:.3f} | {m['particle_grid_iou']:.4f} | {1000*m['reflected_material_error_m']:.3f} | {1000*m['stationary_material_drift_m']:.3f} |")
    lines+=['','All success fields remain null. These examples are excluded from formal attempts.',
            'Ten flat states are evaluated against themselves to characterize the unfolded baseline, not independent rollouts.',
            'The two grasp snapshots share one run and are not independent episodes.',
            'No real successful fold exists here; classification accuracy and thresholds remain unvalidated.']
    (out/'review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':main()
