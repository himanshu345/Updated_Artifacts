#!/usr/bin/env python3
"""collect_dnn_traces.py -- re-collect §VI DNN-architecture energy traces.

Faithful reconstruction of the paper's pipeline (the original collector cell was
not preserved): for each of the 14 lightweight architectures, perform N
independent TRAINING runs on MNIST while a background thread samples the package
RAPL energy counter every ~25 ms, recording the per-sample energy delta until
training completes. Each run -> one <arch>_run<k>.csv with an 'energy_diff'
column, exactly like the originals (trace length scales with training wall-time,
~1 J/sample at ~40 W package).

Model definitions and the training recipe (Adam lr=1e-3, batch=128, 10 epochs)
are copied verbatim from dnn_architectures.ipynb cell 10.

RAPL is root-only on this host, so run as root:
    sudo python3 collect_dnn_traces.py --out OUTDIR [--runs 10] [--epochs 10] [--interval 0.025]
"""
import sys, os, time, csv, argparse, threading
# torch lives in the agv user's site-packages; make it importable under sudo/root
sys.path.insert(0, "/home/agv/.local/lib/python3.8/site-packages")
import torch, torch.nn as nn, torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

RAPL = os.environ.get("RAPL_PATH", "/sys/class/powercap/intel-rapl:0/energy_uj")   # package domain (root-only)
RAPL_MAX = os.environ.get("RAPL_MAX_PATH", "/sys/class/powercap/intel-rapl:0/max_energy_range_uj")

# ---------------- model definitions (verbatim from notebook cell 10) ----------
class NanoCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features=nn.Sequential(nn.Conv2d(1,8,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(8,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Flatten())
        self.classifier=nn.Sequential(nn.Linear(16*7*7,64),nn.ReLU(),nn.Linear(64,10))
    def forward(self,x): return self.classifier(self.features(x))
class PicoCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,6,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(6,12,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Flatten(),
            nn.Linear(12*7*7,40),nn.ReLU(),nn.Linear(40,10))
    def forward(self,x): return self.net(x)
def depthwise_conv(i,o,s=1):
    return nn.Sequential(nn.Conv2d(i,i,3,stride=s,padding=1,groups=i,bias=False),
        nn.BatchNorm2d(i),nn.ReLU(),nn.Conv2d(i,o,1,bias=False),nn.BatchNorm2d(o),nn.ReLU())
class MiniMobileNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.stem=nn.Sequential(nn.Conv2d(1,8,3,padding=1,bias=False),nn.BatchNorm2d(8),nn.ReLU())
        self.ds1=depthwise_conv(8,16); self.ds2=depthwise_conv(16,24)
        self.pool=nn.MaxPool2d(2)
        self.fc=nn.Sequential(nn.Flatten(),nn.Linear(24*7*7,64),nn.ReLU(),nn.Linear(64,10))
    def forward(self,x):
        x=self.stem(x); x=self.ds1(x); x=self.pool(x); x=self.ds2(x); x=self.pool(x); return self.fc(x)
def channel_shuffle(x,groups):
    b,c,h,w=x.size(); cpg=c//groups
    x=x.view(b,groups,cpg,h,w); x=x.transpose(1,2).contiguous(); return x.view(b,-1,h,w)
class ShuffleUnit(nn.Module):
    def __init__(self,in_c,out_c,groups=2):
        super().__init__(); mid=out_c//2
        self.conv_reduce=nn.Conv2d(in_c,mid,1,bias=False)
        self.dw=nn.Conv2d(mid,mid,3,padding=1,groups=mid,bias=False)
        self.conv_expand=nn.Conv2d(mid,out_c,1,bias=False)
        self.bn=nn.BatchNorm2d(out_c); self.relu=nn.ReLU(); self.groups=groups
    def forward(self,x):
        x=self.conv_reduce(x); x=self.dw(x); x=self.conv_expand(x); x=self.bn(x); x=self.relu(x)
        return channel_shuffle(x,self.groups)
class TinyShuffleNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.stem=nn.Conv2d(1,12,3,padding=1); self.stage1=ShuffleUnit(12,24); self.stage2=ShuffleUnit(24,32)
        self.pool=nn.MaxPool2d(2); self.pool2=nn.MaxPool2d(2)
        self.fc=nn.Sequential(nn.Flatten(),nn.Linear(32*7*7,64),nn.ReLU(),nn.Linear(64,10))
    def forward(self,x):
        x=self.stem(x); x=self.stage1(x); x=self.pool(x); x=self.stage2(x); x=self.pool2(x); return self.fc(x)
class TinyDenseLayer(nn.Module):
    def __init__(self,in_ch,growth):
        super().__init__(); self.bn=nn.BatchNorm2d(in_ch)
        self.conv=nn.Conv2d(in_ch,growth,3,padding=1,bias=False); self.relu=nn.ReLU()
    def forward(self,x): return torch.cat([x,self.conv(self.relu(self.bn(x)))],1)
class MicroDenseNet(nn.Module):
    def __init__(self,growth=8):
        super().__init__(); self.init=nn.Conv2d(1,12,3,padding=1,bias=False)
        self.d1_1=TinyDenseLayer(12,growth); self.d1_2=TinyDenseLayer(12+growth,growth); self.d1_3=TinyDenseLayer(12+2*growth,growth)
        self.trans1=nn.Sequential(nn.Conv2d(12+3*growth,20,1,bias=False),nn.AvgPool2d(2))
        self.d2_1=TinyDenseLayer(20,growth); self.d2_2=TinyDenseLayer(20+growth,growth)
        self.pool=nn.AdaptiveAvgPool2d(1); self.fc=nn.Linear(20+2*growth,10)
    def forward(self,x):
        x=self.init(x); x=self.d1_1(x); x=self.d1_2(x); x=self.d1_3(x); x=self.trans1(x)
        x=self.d2_1(x); x=self.d2_2(x); x=self.pool(x).view(x.size(0),-1); return self.fc(x)
class MBConv(nn.Module):
    def __init__(self,in_ch,out_ch,exp=4,stride=1):
        super().__init__(); mid=in_ch*exp
        self.expand=nn.Sequential(nn.Conv2d(in_ch,mid,1,bias=False),nn.BatchNorm2d(mid),nn.ReLU())
        self.dw=nn.Sequential(nn.Conv2d(mid,mid,3,stride=stride,padding=1,groups=mid,bias=False),nn.BatchNorm2d(mid),nn.ReLU())
        self.project=nn.Sequential(nn.Conv2d(mid,out_ch,1,bias=False),nn.BatchNorm2d(out_ch))
        self.use_res=(in_ch==out_ch and stride==1)
    def forward(self,x):
        o=self.expand(x); o=self.dw(o); o=self.project(o); return o+x if self.use_res else o
class TinyEffNet(nn.Module):
    def __init__(self):
        super().__init__(); self.stem=nn.Conv2d(1,8,3,padding=1,bias=False)
        self.mb1=MBConv(8,16,exp=2); self.pool=nn.MaxPool2d(2); self.mb2=MBConv(16,24,exp=2); self.pool2=nn.MaxPool2d(2)
        self.head=nn.Sequential(nn.Flatten(),nn.Linear(24*7*7,64),nn.ReLU(),nn.Linear(64,10))
    def forward(self,x):
        x=self.stem(x); x=self.mb1(x); x=self.pool(x); x=self.mb2(x); x=self.pool2(x); return self.head(x)
class Fire(nn.Module):
    def __init__(self,in_ch,sq,exp):
        super().__init__(); self.squeeze=nn.Conv2d(in_ch,sq,1)
        self.expand1=nn.Conv2d(sq,exp,1); self.expand3=nn.Conv2d(sq,exp,3,padding=1); self.relu=nn.ReLU()
    def forward(self,x):
        s=self.relu(self.squeeze(x)); return torch.cat([self.relu(self.expand1(s)),self.relu(self.expand3(s))],1)
class FireNetMini(nn.Module):
    def __init__(self):
        super().__init__(); self.stem=nn.Conv2d(1,8,3,padding=1); self.fire1=Fire(8,4,4)
        self.pool=nn.MaxPool2d(2); self.fire2=Fire(8,6,6); self.pool2=nn.MaxPool2d(2)
        self.fc=nn.Sequential(nn.Flatten(),nn.Linear(12*7*7,64),nn.ReLU(),nn.Linear(64,10))
    def forward(self,x):
        x=self.stem(x); x=self.fire1(x); x=self.pool(x); x=self.fire2(x); x=self.pool2(x); return self.fc(x)
class TinyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,6,5),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(6,16,5),nn.ReLU(),nn.MaxPool2d(2),
            nn.Flatten(),nn.Linear(16*4*4,120),nn.ReLU(),nn.Linear(120,84),nn.ReLU(),nn.Linear(84,10))
    def forward(self,x): return self.net(x)
class MicroCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,4,3),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(4,8,3),nn.ReLU(),nn.MaxPool2d(2),
            nn.Flatten(),nn.Linear(8*5*5,32),nn.ReLU(),nn.Linear(32,10))
    def forward(self,x): return self.net(x)
class DSConv(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,4,3,padding=1),nn.ReLU(),nn.Conv2d(4,4,3,padding=1,groups=4),nn.ReLU(),
            nn.Conv2d(4,8,1),nn.ReLU(),nn.MaxPool2d(2),nn.Flatten(),nn.Linear(8*14*14,10))
    def forward(self,x): return self.net(x)
class SqueezeTiny(nn.Module):
    def __init__(self):
        super().__init__(); self.squeeze=nn.Conv2d(1,4,1); self.expand=nn.Conv2d(4,8,3,padding=1)
        self.pool=nn.MaxPool2d(2); self.fc=nn.Sequential(nn.Flatten(),nn.Linear(8*14*14,10))
    def forward(self,x): x=self.squeeze(x); x=self.expand(x); x=self.pool(x); return self.fc(x)
class BasicBlock(nn.Module):
    def __init__(self,in_ch,out_ch):
        super().__init__(); self.conv1=nn.Conv2d(in_ch,out_ch,3,padding=1); self.bn1=nn.BatchNorm2d(out_ch)
        self.relu=nn.ReLU(); self.conv2=nn.Conv2d(out_ch,out_ch,3,padding=1); self.bn2=nn.BatchNorm2d(out_ch)
    def forward(self,x):
        o=self.conv1(x); o=self.bn1(o); o=self.relu(o); o=self.conv2(o); o=self.bn2(o); o+=x; return self.relu(o)
class TinyResNet(nn.Module):
    def __init__(self):
        super().__init__(); self.stem=nn.Conv2d(1,8,3,padding=1); self.block1=BasicBlock(8,8)
        self.pool=nn.MaxPool2d(2); self.block2=BasicBlock(8,8); self.pool2=nn.MaxPool2d(2)
        self.fc=nn.Sequential(nn.Flatten(),nn.Linear(8*7*7,10))
    def forward(self,x):
        x=self.stem(x); x=self.block1(x); x=self.pool(x); x=self.block2(x); x=self.pool2(x); return self.fc(x)
class InceptionTiny(nn.Module):
    def __init__(self,in_ch,o1,o3,o5):
        super().__init__(); self.b1=nn.Sequential(nn.Conv2d(in_ch,o1,1),nn.ReLU())
        self.b3=nn.Sequential(nn.Conv2d(in_ch,o3,3,padding=1),nn.ReLU()); self.b5=nn.Sequential(nn.Conv2d(in_ch,o5,5,padding=2),nn.ReLU())
    def forward(self,x): return torch.cat([self.b1(x),self.b3(x),self.b5(x)],1)
class TinyGoogLeNet(nn.Module):
    def __init__(self):
        super().__init__(); self.stem=nn.Conv2d(1,16,3,padding=1); self.inc1=InceptionTiny(16,8,8,8)
        self.pool=nn.MaxPool2d(2); self.inc2=InceptionTiny(24,12,12,12); self.fc=nn.Linear(36*14*14,10)
    def forward(self,x):
        x=self.stem(x); x=self.inc1(x); x=self.pool(x); x=self.inc2(x); x=x.view(x.size(0),-1); return self.fc(x)
class LeNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(1,6,5),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(6,16,5),nn.ReLU(),nn.MaxPool2d(2),
            nn.Flatten(),nn.Linear(16*4*4,120),nn.ReLU(),nn.Linear(120,84),nn.ReLU(),nn.Linear(84,10))
    def forward(self,x): return self.net(x)

# the exact 14 architectures present in the original trace set
REGISTRY = {
    "dsconv":DSConv, "firenetmini":FireNetMini, "lenet":LeNet, "microcnn":MicroCNN,
    "microdensenet":MicroDenseNet, "minimobilenet":MiniMobileNet, "nanocnn":NanoCNN,
    "picocnn":PicoCNN, "squeezetiny":SqueezeTiny, "tinycnn":TinyCNN, "tinyeffnet":TinyEffNet,
    "tinygooglenet":TinyGoogLeNet, "tinyresnet":TinyResNet, "tinyshufflenet":TinyShuffleNet,
}

def read_energy():
    with open(RAPL) as f: return int(f.read())
def read_max():
    try:
        with open(RAPL_MAX) as f: return int(f.read())
    except Exception: return None

class Sampler(threading.Thread):
    """Background: read package RAPL every `interval` s, record wrap-corrected deltas."""
    def __init__(self, interval):
        super().__init__(daemon=True)
        self.interval=interval; self.stop=threading.Event(); self.deltas=[]
        self.max=read_max()
    def run(self):
        prev=read_energy(); nxt=time.perf_counter()+self.interval
        while not self.stop.is_set():
            now=time.perf_counter()
            if now<nxt: time.sleep(max(0,min(self.interval,nxt-now))); continue
            nxt+=self.interval
            cur=read_energy()
            d=cur-prev
            if d<0 and self.max: d+=self.max      # counter wrap
            self.deltas.append(d); prev=cur

def train_once(model, loader, epochs):
    opt=optim.Adam(model.parameters(), lr=1e-3); lossf=nn.CrossEntropyLoss()
    model.train()
    for _ in range(epochs):
        for X,y in loader:
            opt.zero_grad(); loss=lossf(model(X),y); loss.backward(); opt.step()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True); ap.add_argument("--runs",type=int,default=10)
    ap.add_argument("--epochs",type=int,default=10); ap.add_argument("--interval",type=float,default=0.025)
    ap.add_argument("--batch",type=int,default=128)
    a=ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if os.geteuid()!=0: print("WARNING: not root; package RAPL is root-only.", file=sys.stderr)
    tfm=transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,),(0.3081,))])
    ds=datasets.MNIST(root=os.path.join(a.out,"mnist"), train=True, download=True, transform=tfm)
    loader=DataLoader(ds, batch_size=a.batch, shuffle=True, num_workers=2)
    print(f"interval={a.interval*1000:.0f}ms runs={a.runs} epochs={a.epochs} archs={len(REGISTRY)} "
          f"rapl_max={read_max()}", flush=True)
    t_all=time.time()
    for name,cls in REGISTRY.items():
        for run in range(a.runs):
            torch.manual_seed(run)                 # independent runs, reproducible
            model=cls()
            s=Sampler(a.interval); t0=time.time(); s.start()
            train_once(model, loader, a.epochs)
            s.stop.set(); s.join(timeout=1.0)
            out=os.path.join(a.out, f"{name}_run{run}.csv")
            with open(out,"w",newline="") as f:
                w=csv.writer(f); w.writerow(["energy_diff"])
                for d in s.deltas: w.writerow([d])
            print(f"{name:16} run{run} | {len(s.deltas):5d} samples | {time.time()-t0:6.1f}s", flush=True)
    print(f"DONE in {(time.time()-t_all)/60:.1f} min -> {a.out}", flush=True)

if __name__=="__main__":
    main()
