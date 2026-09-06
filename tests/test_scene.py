import torch
from ruthless_pipeline import GarmentSceneBatch, GarmentTextureComposer


def test_scene_composer_gradient():
    base=torch.zeros(2,3,32,32)
    mask=torch.zeros(2,1,32,32); mask[:,:,8:24,8:24]=1
    tex=torch.rand(1,3,8,8,requires_grad=True)
    out=GarmentTextureComposer(tile=True).compose(GarmentSceneBatch(base,mask),tex)
    assert out.shape==base.shape
    out.mean().backward()
    assert tex.grad is not None and torch.isfinite(tex.grad).all()
