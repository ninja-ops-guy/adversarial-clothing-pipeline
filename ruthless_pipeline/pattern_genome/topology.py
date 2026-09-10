from __future__ import annotations
import numpy as np
from scipy import ndimage
from .color import _kmeans_palette
from .schema import TopologyGenome

def _sym(a,b):
    x=a.astype(float)/255.0; y=b.astype(float)/255.0
    return float(max(0.0,1.0-np.mean(np.abs(x-y))))

def extract_topology(rgb, max_colors=8, seed=1337, iterations=20, connectivity=8):
    _, labels=_kmeans_palette(rgb,max_colors,seed,iterations); counts=np.bincount(labels.ravel()); bg=int(np.argmax(counts)); fg=labels!=bg
    structure=ndimage.generate_binary_structure(2,2 if connectivity==8 else 1); lab,n=ndimage.label(fg,structure)
    areas=np.bincount(lab.ravel())[1:] if n else np.array([],dtype=int); total=fg.size
    comps=(areas/total) if len(areas) else np.array([],float)
    filled=ndimage.binary_fill_holes(fg); holes=filled & ~fg; _,hn=ndimage.label(holes,structure)
    er=ndimage.binary_erosion(fg,structure=structure,border_value=0); edge=fg & ~er
    f=fg.astype(float); F=np.fft.fft2(f-f.mean()); ac=np.fft.ifft2(np.abs(F)**2).real; ac=np.fft.fftshift(ac); c=(ac.shape[0]//2,ac.shape[1]//2); ac[c]=0; peak=np.unravel_index(np.argmax(ac),ac.shape); denom=float(np.max(np.abs(ac))) or 1.0
    py=float(abs(peak[0]-c[0])); px=float(abs(peak[1]-c[1])); ap=float(max(0.0,ac[peak]/denom))
    frag=float(n/max(fg.sum(),1))
    return TopologyGenome(int(n), float(comps.max() if len(comps) else 0), float(comps.mean() if len(comps) else 0), float(np.median(comps) if len(comps) else 0), float(comps.std() if len(comps) else 0), int(hn), int(n-hn), float(edge.mean()), _sym(rgb,np.flipud(rgb)), _sym(rgb,np.fliplr(rgb)), _sym(rgb,np.transpose(rgb,(1,0,2))[:rgb.shape[0],:rgb.shape[1]]) if rgb.shape[0]==rgb.shape[1] else 0.0, _sym(rgb,np.fliplr(np.transpose(rgb,(1,0,2)))[:rgb.shape[0],:rgb.shape[1]]) if rgb.shape[0]==rgb.shape[1] else 0.0, _sym(rgb,np.rot90(rgb,2)), ap, px, py, frag)
