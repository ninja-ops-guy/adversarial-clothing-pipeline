from __future__ import annotations
import numpy as np
from .schema import SpectralGenome

def _lum(rgb):
    x=rgb.astype(np.float64)/255.0
    return 0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]

def extract_spectral(rgb: np.ndarray, radial_bins:int=8, fft_window:str="hann") -> SpectralGenome:
    y=_lum(rgb); y=y-y.mean()
    if fft_window=="hann": y=y*np.outer(np.hanning(y.shape[0]),np.hanning(y.shape[1]))
    p=np.abs(np.fft.fftshift(np.fft.fft2(y)))**2
    h,w=p.shape; yy,xx=np.indices((h,w)); cy=(h-1)/2; cx=(w-1)/2
    r=np.sqrt(((yy-cy)/(max(h,1)/2))**2+((xx-cx)/(max(w,1)/2))**2)
    mask=r<=1.0; total=float(p[mask].sum())
    if total<=0: energies=np.zeros(radial_bins); energies[0]=1.0
    else:
        edges=np.linspace(0,1,radial_bins+1); energies=[]
        for i in range(radial_bins):
            m=mask & (r>=edges[i]) & ((r<edges[i+1]) if i<radial_bins-1 else (r<=edges[i+1]))
            energies.append(float(p[m].sum()/total))
        energies=np.asarray(energies); energies=energies/energies.sum()
    centers=(np.arange(radial_bins)+0.5)/radial_bins
    centroid=float(np.dot(energies,centers))
    nz=energies[energies>0]; entropy=float(-(nz*np.log2(nz)).sum()/np.log2(radial_bins)) if radial_bins>1 else 0.0
    gy,gx=np.gradient(y); mag=np.hypot(gx,gy); angles=(np.degrees(np.arctan2(gy,gx))+180)%180
    bins=np.linspace(0,180,37); hist,_=np.histogram(angles,bins=bins,weights=mag)
    k=int(hist.argmax()); dom=float((bins[k]+bins[k+1])/2); strength=float(hist[k]/hist.sum()) if hist.sum()>0 else 0.0
    return SpectralGenome(tuple(float(v) for v in energies), float(energies[:2].sum()), float(energies[2:5].sum()), float(energies[5:].sum()), centroid, entropy, dom, strength)
