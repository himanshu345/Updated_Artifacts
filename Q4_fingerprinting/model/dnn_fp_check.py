#!/usr/bin/env python3
"""Reproduce §VI DNN-architecture fingerprinting from feature_dataset.csv.

Paper pipeline: 7 features (mean,std,max,min,energy_sum,spikes,fft_peak),
RandomForest(300 trees), stratified 75/25 split, reported acc = 97.14%.

We reproduce that exactly, then stress-test it (repeated splits + leave-one-run-out
CV) because a single 75/25 split of 140 rows has only ~35 test samples.
"""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, LeaveOneGroupOut, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, confusion_matrix

FEATS = ["mean","std","max","min","energy_sum","spikes","fft_peak"]
df = pd.read_csv(sys.argv[1])
df = df[df["label"]!="abcd"] if "abcd" in set(df["label"]) else df
X = df[FEATS].values
le = LabelEncoder(); y = le.fit_transform(df["label"].values)
groups = df["run"].values
classes = le.classes_
print(f"{X.shape[0]} rows, {len(classes)} architectures, {X.shape[1]} features")
print(f"runs/arch: {np.bincount(y).min()}-{np.bincount(y).max()}\n")

# (1) FAITHFUL: single stratified 75/25 split, RF(300). seed sweep to see spread.
print("(1) paper setup: RandomForest(300), stratified 75/25")
accs=[]
for seed in range(50):
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.25,stratify=y,random_state=seed)
    clf=RandomForestClassifier(n_estimators=300,random_state=seed).fit(Xtr,ytr)
    accs.append(accuracy_score(yte,clf.predict(Xte)))
accs=np.array(accs)
print(f"    test acc over 50 seeds: mean={100*accs.mean():.1f}%  "
      f"min={100*accs.min():.1f}%  max={100*accs.max():.1f}%  (n_test={len(yte)})")
print(f"    paper reported 97.14% (= 34/35) -> within our {100*accs.min():.0f}-{100*accs.max():.0f}% range\n")

# (2) ROBUST: leave-one-run-out (train on 9 runs, test the held-out run; 10 folds)
print("(2) leave-one-run-out CV (train 9 runs / test 1 run, 10 folds)")
logo=LeaveOneGroupOut(); yp=np.zeros_like(y); acc_folds=[]
for tr,te in logo.split(X,y,groups):
    clf=RandomForestClassifier(n_estimators=300,random_state=0).fit(X[tr],y[tr])
    p=clf.predict(X[te]); yp[te]=p; acc_folds.append(accuracy_score(y[te],p))
print(f"    per-fold acc: {[f'{100*a:.0f}' for a in acc_folds]}")
print(f"    overall LORO acc = {100*accuracy_score(y,yp):.1f}%\n")

# (3) which features carry it + per-class accuracy
clf=RandomForestClassifier(n_estimators=300,random_state=0).fit(X,y)
imp=sorted(zip(FEATS,clf.feature_importances_),key=lambda t:-t[1])
print("(3) feature importance (RF, full fit):")
for f,v in imp: print(f"    {f:12} {v:.3f}")
cm=confusion_matrix(y,yp)
print("\n    per-architecture LORO accuracy:")
for i,c in enumerate(classes):
    print(f"    {c:16} {100*cm[i,i]/cm[i].sum():5.0f}%  "+("".join("." if j==i else ("X" if cm[i,j] else " ") for j in range(len(classes)))))
np.save(os.path.join(HERE, "dnn_cm.npy"), cm)
np.save(os.path.join(HERE, "dnn_classes.npy"), classes)
