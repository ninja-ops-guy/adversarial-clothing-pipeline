from __future__ import annotations
import numpy as np
from scipy import ndimage
from .color import _kmeans_palette
from .schema import GeometryGenome

def _entropy_from_hist(hist: np.ndarray) -> float:
    p=hist.astype(float).ravel(); s=p.sum()
    if s<=0: return 0.0
    p=p/s; p=p[p>0]
    denom=np.log2(len(hist.ravel())) if len(hist.ravel())>1 else 1.0
    return float(-(p*np.log2(p)).sum()/denom)

def extract_geometry(rgb: np.ndarray, max_colors:int=8, seed:int=1337, iterations:int=20, spatial_hist_bins:int=16) -> GeometryGenome:
    _, labels=_kmeans_palette(rgb,max_colors,seed,iterations)
    counts=np.bincount(labels.ravel()); bg=int(np.argmax(counts)); fg=labels!=bg
    h,w=fg.shape; area=int(fg.sum()); coverage=float(area/(h*w))
    if area:
        yy,xx=np.nonzero(fg)
        cy=float(yy.mean()/max(h-1,1)); cx=float(xx.mean()/max(w-1,1))
        bh=int(yy.max()-yy.min()+1); bw=int(xx.max()-xx.min()+1); bbox=float((bh*bw)/(h*w))
        dist=ndimage.distance_transform_edt(fg); maxima=(dist==ndimage.maximum_filter(dist,size=3)) & fg
        widths=2.0*dist[maxima]
        if widths.size==0: widths=2.0*dist[fg]
        meanw=float(widths.mean()) if widths.size else 0.0
        medw=float(np.median(widths)) if widths.size else 0.0
        minw=float(widths.min()) if widths.size else 0.0
        hist,_,_=np.histogram2d(yy,xx,bins=spatial_hist_bins,range=[[0,h],[0,w]])
        sent=_entropy_from_hist(hist)
    else:
        cx=cy=bbox=meanw=medw=minw=sent=0.0
    er=ndimage.binary_erosion(fg,border_value=0); edge=fg & ~er
    edge_to_area=float(edge.sum()/max(area,1))
    x=rgb.astype(float)/255.0; lum=0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]
    hm,wm=h//2,w//2
    quads=(lum[:hm,:wm],lum[:hm,wm:],lum[hm:,:wm],lum[hm:,wm:])
    qe=tuple(float(q.mean()) if q.size else 0.0 for q in quads)
    norm=max(min(h,w),1)
    return GeometryGenome(coverage,edge_to_area,meanw,medw,minw,meanw/norm,minw/norm,bbox,cx,cy,qe,sent)
