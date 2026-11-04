#!/usr/bin/env python3
"""D2-A release kinematics: pre-release hold, attachment-off step and first 30 steps."""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

SURFACE='#fcfcfb'; INK='#0b0b0b'; SECONDARY='#52514e'; GRID='#e1e0d9'
AXIS='#c3c2b7'; BLUE='#2a78d6'; ORANGE='#eb6834'; CRITICAL='#d03b3b'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,
    'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,
    'legend.fontsize':7.5,'figure.facecolor':SURFACE,'axes.facecolor':SURFACE,
    'savefig.facecolor':SURFACE})


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def npz(p):
    with np.load(p,allow_pickle=False) as z: return {k:z[k].copy() for k in z.files}
def angle2d(a,b):
    a=np.asarray(a,float)[:,:2]; b=np.asarray(b,float)[:,:2]
    ca,cb=a.mean(0),b.mean(0); h=(a-ca).T@(b-cb); u,s,vt=np.linalg.svd(h); r=vt.T@u.T
    if np.linalg.det(r)<0: vt[-1,:]*=-1; r=vt.T@u.T
    return math.degrees(math.atan2(r[1,0],r[0,0]))
def interval_stats(V,dt,i,j):
    ps=[]; cs=[]; ws=[]
    for k in range(i,j):
        d=np.linalg.norm(V[k+1]-V[k],axis=1)*1000
        ps.append(float(d.mean())/dt)
        cs.append(float(np.linalg.norm(V[k+1].mean(0)-V[k].mean(0))*1000)/dt)
        ws.append(abs(angle2d(V[k],V[k+1]))/dt)
    ps=np.asarray(ps); cs=np.asarray(cs); ws=np.asarray(ws)
    return {'n_intervals':len(ps),'particle_mean_speed_mean_mm_s':float(ps.mean()),
            'particle_mean_speed_max_mm_s':float(ps.max()),
            'centroid_speed_mean_mm_s':float(cs.mean()),
            'centroid_speed_max_mm_s':float(cs.max()),
            'angular_speed_mean_deg_s':float(ws.mean()),
            'angular_speed_max_deg_s':float(ws.max())}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--d1',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); d1=a.d1.resolve(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    hold=npz(d1/'pre_release_hold.npz'); Vh=hold['vertices']; dth=float(hold['dt_s'])
    rd=npz(d1/'evidence/release_diag.npz')
    m=np.asarray(rd['sample_label'])==''
    st=np.asarray(rd['observed_step'])[m]; tt=np.asarray(rd['sim_time_s'])[m]
    V=np.asarray(rd['vertices'])[m]; dt=1/60
    def idx(s): return int(np.where(st==s)[0][0])
    intervals={
        'prehold_last5':interval_stats(Vh,dth,174,179),
        'prehold_last30':interval_stats(Vh,dth,149,179),
        'prehold_all':interval_stats(Vh,dth,0,179),
        'attachment_off_1943_1944':interval_stats(V,dt,idx(1943),idx(1944)),
        'post_release_first5':interval_stats(V,dt,idx(1944),idx(1949)),
        'post_release_first10':interval_stats(V,dt,idx(1944),idx(1954)),
        'post_release_first30':interval_stats(V,dt,idx(1944),idx(1974)),
        'wait_first30':interval_stats(V,dt,idx(1954),idx(1984)),
        'wait_last30':interval_stats(V,dt,idx(2044),idx(2074)),
        'post30_to_wait_end':interval_stats(V,dt,idx(1974),idx(2074)),
    }
    # Fix a typo-free copy of the release interval (kept explicit).
    intervals['attachment_off_1943_1944']=interval_stats(V,dt,idx(1943),idx(1944))
    timing=[]
    for s in (1943,1944,1953,1954):
        i=idx(s)
        raw=int(np.where(np.asarray(rd['observed_step'])==s)[0][0])
        timing.append({'observed_step':s,'sim_time_s':float(tt[i]),
            'holding':bool(rd['holding'][raw]),'attached':bool(rd['attached'][raw]),
            'enabled_slots':[bool(x) for x in rd['enabled_slots'][raw]],
            'logical_attached':bool(rd['logical_attached'][raw]),
            'command_holding':bool(rd['command_holding'][raw]),
            'gripper_state':int(rd['gripper_state'][raw]),
            'z_min_m':float(V[i,:,2].min()),'z_max_m':float(V[i,:,2].max())})
    # Per-step series for plot.
    steps=st[idx(1943):idx(2000)+1]
    ps=[]; cs=[]; ws=[]
    for k in range(idx(1943),idx(2000)):
        d=np.linalg.norm(V[k+1]-V[k],axis=1)*1000
        ps.append(float(d.mean())/dt)
        cs.append(float(np.linalg.norm(V[k+1].mean(0)-V[k].mean(0))*1000)/dt)
        ws.append(abs(angle2d(V[k],V[k+1]))/dt)
    payload={'d1':str(d1),'prehold_dt_s':dth,'intervals':intervals,'timing':timing,
             'support_z_min_m':float(V[:,:,2].min()),
             'note':'speeds are backward differences between consecutive state rows; '
                    'particle mean speed is the mean over 441 vertices; angular speed is '
                    'the 2D rigid fit between consecutive frames.'}
    (out/'release_kinematics.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    with (out/'release_kinematics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['interval','intervals','particle_mean_speed_mean_mm_s',
            'particle_mean_speed_max_mm_s','centroid_speed_mean_mm_s',
            'centroid_speed_max_mm_s','angular_speed_mean_deg_s','angular_speed_max_deg_s'])
        for k,v in intervals.items():
            w.writerow([k,v['n_intervals'],v['particle_mean_speed_mean_mm_s'],
                v['particle_mean_speed_max_mm_s'],v['centroid_speed_mean_mm_s'],
                v['centroid_speed_max_mm_s'],v['angular_speed_mean_deg_s'],
                v['angular_speed_max_deg_s']])
    with (out/'attachment_timing.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['observed_step','sim_time_s','holding','attached',
            'enabled_slots','logical_attached','command_holding','gripper_state',
            'z_min_m','z_max_m'])
        for r in timing:
            w.writerow([r['observed_step'],r['sim_time_s'],r['holding'],r['attached'],
                r['enabled_slots'],r['logical_attached'],r['command_holding'],
                r['gripper_state'],r['z_min_m'],r['z_max_m']])
    fig,axes=plt.subplots(2,1,figsize=(8.4,5.4),sharex=True)
    axes[0].plot(steps[:-1],ps,color=BLUE,lw=1.8,label='particle mean speed')
    axes[0].plot(steps[:-1],cs,color=ORANGE,lw=1.8,label='centroid speed')
    axes[0].set_ylabel('speed (mm/s)'); axes[0].legend(loc='upper right')
    axes[0].set_title('Release-window cloth speeds (backward differences)')
    axes[1].plot(steps[:-1],ws,color=BLUE,lw=1.8)
    axes[1].set_ylabel('angular speed (deg/s)'); axes[1].set_xlabel('observed step')
    for ax in axes:
        ax.grid(color=GRID,lw=.7); ax.set_axisbelow(True)
        for s in ('top','right'): ax.spines[s].set_visible(False)
        for s in ('left','bottom'): ax.spines[s].set_color(AXIS)
        ax.axvline(1944,color=CRITICAL,ls='--',lw=1)
        ax.axvline(1953,color=SECONDARY,ls=':',lw=1)
        ax.axvline(1954,color=SECONDARY,ls='--',lw=1)
    axes[0].text(1945,0.93,'attachment off 1944',transform=axes[0].get_xaxis_transform(),
                 fontsize=7.2,color=CRITICAL)
    axes[0].text(1955,0.80,'ungrasp return 1953 / gripper open 1954',
                 transform=axes[0].get_xaxis_transform(),fontsize=7.2,color=SECONDARY)
    fig.tight_layout(); fig.savefig(out/'d2_a_release_speeds.png',dpi=180); plt.close(fig)
    print('D2_A_KINEMATICS_OK')
    for k,v in intervals.items(): print(k,v)
    print('timing',json.dumps(timing,indent=1))
    return 0

if __name__=='__main__': raise SystemExit(main())
