"""Read-only geometry audit of historical development evidence. Never promote success."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from stage4_success_v1 import geometry, identity


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    rows=[];skipped=[]
    for root in args.root:
        for file in sorted(root.rglob('metrics_full.json')):
            r=json.loads(file.read_text(encoding='utf-8'));d=file.parent
            names=['00_initial.npz','06_final_3s.npz'] if r['task']=='l1' else ['recovered.npz','final.npz']
            paths=[d/n for n in names]+[d/'cloth_constructed.npz']
            if not all(q.exists() for q in paths):
                skipped.append(str(d));continue
            if r['task']=='l1' and r['fold_overhang_m']!=.02:
                # Legacy nominal L1 remains a negative/control for task A, not task B coverage.
                task='A_l1_overfold'
            else:task='A_l1_overfold' if r['task']=='l1' else 'B_nominal'
            with np.load(paths[0],allow_pickle=False) as z:a=z['vertices']
            with np.load(paths[1],allow_pickle=False) as z:b=z['vertices']
            with np.load(paths[2],allow_pickle=False) as z:lp=z['points']
            g=geometry(a,b,lp,int(r['pick_index']),r['fold_yaw_rad'],r['fold_edge'],task)
            rows.append({'directory':str(d),'task':task,'seed':r['seed'],'overhang':r['fold_overhang_m'],'edge':r['fold_edge'],'legacy_passed':r['passed'],'geometry':g,'evidence_hashes':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in [file,*paths]},'criteria_status':'incomplete','criteria_success':None,'reason':'No full step0..330 release/state/geometry trace; no retrospective formal promotion'})
    report={'evaluator_files':identity(),'rows':rows,'skipped_missing_geometry':skipped,'counts':{'directories':len(rows),'geometry_pass':sum(r['geometry']['geometry_pass'] for r in rows),'formal_successes_added':0},'scope':'Repeated modes and repeated directories are not independent seeds. Historical nominal L1 controls are not task B validation.'}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(report['counts']))

if __name__=='__main__':main()
