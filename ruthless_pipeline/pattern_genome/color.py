from __future__ import annotations
import numpy as np
from .schema import ColorGenome

def _rgb_to_lab(rgb):
    x=rgb.astype(np.float64)/255.0
    x=np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
    M=np.array([[0.4124564,0.3575761,0.1804375],[0.2126729,0.7151522,0.0721750],[0.0193339,0.1191920,0.9503041]])
    xyz=x@M.T; ref=np.array([0.95047,1.0,1.08883]); q=xyz/ref
    d=6/29; f=np.where(q>d**3,np.cbrt(q),q/(3*d*d)+4/29)
    L=116*f[...,1]-16; a=500*(f[...,0]-f[...,1]); b=200*(f[...,1]-f[...,2]); return np.stack([L,a,b],axis=-1)

def _kmeans_palette(rgb, k, seed=1337, iterations=20):
    pts=rgb.reshape(-1,3).astype(np.float64)/255.0
    if len(pts)==0: raise ValueError("empty image")
    uniq=np.unique(pts,axis=0); k=min(k,len(uniq))
    first=seed % len(pts); centers=[pts[first]]
    for _ in range(1,k):
        D=np.min(np.stack([((pts-c)**2).sum(1) for c in centers],axis=1),axis=1); centers.append(pts[int(np.argmax(D))])
    centers=np.stack(centers)
    for _ in range(iterations):
        dist=((pts[:,None,:]-centers[None,:,:])**2).sum(2); labels=dist.argmin(1); new=centers.copy()
        for j in range(k):
            if np.any(labels==j): new[j]=pts[labels==j].mean(0)
        if np.allclose(new,centers,atol=1e-8,rtol=0): centers=new; break
        centers=new
    lum=0.2126*centers[:,0]+0.7152*centers[:,1]+0.0722*centers[:,2]; order=np.argsort(lum); centers=centers[order]
    dist=((pts[:,None,:]-centers[None,:,:])**2).sum(2); labels=dist.argmin(1).reshape(rgb.shape[:2])
    return centers, labels

def extract_color(rgb, max_colors=8, seed=1337, iterations=20):
    x=rgb.astype(np.float64)/255.0; flat=x.reshape(-1,3); lab=_rgb_to_lab(rgb); labf=lab.reshape(-1,3)
    centers,labels=_kmeans_palette(rgb,max_colors,seed,iterations); counts=np.bincount(labels.ravel(),minlength=len(centers)); fracs=counts/counts.sum()
    centers_lab=_rgb_to_lab(np.clip(np.round(centers*255),0,255).astype(np.uint8).reshape(1,-1,3)).reshape(-1,3)
    ds=[]
    for i in range(len(centers_lab)):
        for j in range(i+1,len(centers_lab)): ds.append(float(np.linalg.norm(centers_lab[i]-centers_lab[j])))
    pal=tuple({"lab":[float(v) for v in centers_lab[i]],"fraction":float(fracs[i])} for i in range(len(centers)))
    lum=0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]; chroma=np.hypot(lab[...,1],lab[...,2]); nz=fracs[fracs>0]
    cov=np.cov(labf,rowvar=False,bias=True) if len(labf)>1 else np.zeros((3,3))
    return ColorGenome(len(centers), tuple(map(float,flat.mean(0))), tuple(map(float,flat.std(0))), tuple(map(float,labf.mean(0))), tuple(tuple(float(v) for v in row) for row in cov), float(np.ptp(labf[:,0])), float(np.ptp(labf[:,1])), float(np.ptp(labf[:,2])), float(np.mean(ds) if ds else 0), float(np.max(ds) if ds else 0), float(lum.std()), float(chroma.std()), float(-(nz*np.log2(nz)).sum()), pal)
