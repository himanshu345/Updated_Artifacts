#!/usr/bin/env python3
"""extract_and_classify.py -- build the 7-feature table from a directory of
<arch>_run<k>.csv energy traces, then reproduce the §VI Random-Forest
fingerprinting (faithful 75/25 + leave-one-run-out CV).

Feature definitions validated to reproduce the original feature_dataset.csv
exactly (140/140 rows on all 7 features):
    mean,std,max,min,energy_sum = basic stats of the energy_diff series
    spikes   = count of samples strictly above the 95th percentile
    fft_peak = argmax(|rfft(x - mean)|[1:])   (dominant non-DC frequency bin)

Usage: python3 extract_and_classify.py <trace_dir> [--save feature_dataset.csv]
"""
import sys, os, glob, argparse, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, LeaveOneGroupOut
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, confusion_matrix

FEATS=["mean","std","max","min","energy_sum","spikes","fft_peak"]

def feats(x):
    x=x.astype(float)
    return dict(mean=x.mean(),std=x.std(),max=x.max(),min=x.min(),energy_sum=x.sum(),
                spikes=int((x>np.percentile(x,95)).sum()),
                fft_peak=int(np.argmax(np.abs(np.fft.rfft(x-x.mean()))[1:])))

def build(trace_dir):
    rows=[]
    for f in sorted(glob.glob(os.path.join(trace_dir,"*_run*.csv"))):
        b=os.path.basename(f)
        if b=="feature_dataset.csv": continue
        lab="_".join(b.split("_")[:-1]); run=int(b.split("_run")[1].split(".")[0])
        x=np.loadtxt(f,skiprows=1)
        if x.ndim==0 or len(np.atleast_1d(x))<2: continue
        d=feats(np.atleast_1d(x)); d["label"]=lab; d["run"]=run; rows.append(d)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("trace_dir"); ap.add_argument("--save")
    a=ap.parse_args()
    df=build(a.trace_dir)
    if a.save: df.to_csv(a.save,index=False); print("wrote",a.save)
    X=df[FEATS].values; le=LabelEncoder(); y=le.fit_transform(df["label"]); g=df["run"].values
    cls=le.classes_
    print(f"{len(df)} traces, {len(cls)} architectures, runs/arch {np.bincount(y).min()}-{np.bincount(y).max()}\n")
    # faithful 75/25 over 50 seeds -- only if the test fold can hold >=1 per class
    n_test=int(round(0.25*len(y)))
    if n_test>=len(cls):
        accs=[]
        for s in range(50):
            Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.25,stratify=y,random_state=s)
            accs.append(accuracy_score(yte,RandomForestClassifier(300,random_state=s).fit(Xtr,ytr).predict(Xte)))
        accs=np.array(accs)
        print(f"RF(300) stratified 75/25: {100*accs.mean():.1f}% mean  [{100*accs.min():.0f}-{100*accs.max():.0f}%]  (paper 97.14%)")
    else:
        print(f"RF(300) stratified 75/25: skipped (only {np.bincount(y).min()} runs/class -> "
              f"test fold {n_test} < {len(cls)} classes; use leave-one-run-out below)")
    # leave-one-run-out
    logo=LeaveOneGroupOut(); yp=np.zeros_like(y)
    for tr,te in logo.split(X,y,g):
        yp[te]=RandomForestClassifier(300,random_state=0).fit(X[tr],y[tr]).predict(X[te])
    print(f"leave-one-run-out CV:     {100*accuracy_score(y,yp):.1f}%\n")
    cm=confusion_matrix(y,yp)
    print("per-architecture LORO accuracy:")
    for i,c in enumerate(cls):
        print(f"  {c:16} {100*cm[i,i]/cm[i].sum():5.0f}%")
    np.save(os.path.join(a.trace_dir,"_cm.npy"),cm); np.save(os.path.join(a.trace_dir,"_classes.npy"),cls)

if __name__=="__main__": main()
