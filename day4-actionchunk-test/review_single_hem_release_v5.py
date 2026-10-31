import json,sys
from pathlib import Path
import numpy as np
from minimum_fold_geometry import support_summary
base=Path(__file__).resolve().parent
out=base/'results/day4-minimum-half-fold-20261031-060323-618705'
r=json.loads((out/'result.json').read_text());p=dict(np.load(out/'fold_definition.npz'));rows={}
for stage in ['00_initial','02_grasp','06_supported_place','07_released','08_release_stationary','11_retention_4s']:
 d=np.load(out/(stage+'.npz'));v=d['vertices'];ids=d['anchors_2'];assert ids.tolist()==[int(p['pick_index'])]
 rows[stage]={'anchor_ids':ids.tolist(),'pick':v[int(p['pick_index'])].tolist(),'support':support_summary(v,p['source_mask'],int(p['pick_index']))}
h=np.load(out/'terminal_hold_trace.npz');speed=np.linalg.norm(np.diff(h['vertices'][-31:,p['source_mask']],axis=0),axis=2)/float(h['dt'])
a={'stages':rows,'source_speed_p95_m_s':float(np.percentile(speed,95)),'material_goal_error_m':r['material_goal_error_m'],'max_anchor_gap_m':r['hem_single_anchor_max_gap_m'],'lifecycle_checks':r['lifecycle_checks'],'errors':r['errors'],'retention_metrics':r['retention_metrics'],'recoil_mm':float(np.linalg.norm(np.array(rows['08_release_stationary']['pick'])[:2]-np.array(rows['06_supported_place']['pick'])[:2])*1000)}
(out/'release_audit.json').write_text(json.dumps(a,indent=2),encoding='utf-8');print(json.dumps(a,indent=2))
