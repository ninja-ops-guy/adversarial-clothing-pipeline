from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional

import torch
import torch.nn.functional as F

from .common import atomic_json_dump, ensure_dir, resolve_device, seed_everything, validate_image_tensor


@dataclass
class DifferentiablePhysicsConfig:
    grid_size: tuple[int, int] = (24, 24)
    image_resolution: tuple[int, int] = (256, 256)
    simulation_steps: int = 40
    dt: float = 0.01
    mass_density: float = 0.2
    structural_stiffness: float = 60.0
    bend_stiffness: float = 8.0
    damping: float = 2.0
    solver_substeps: int = 8
    gravity: tuple[float, float, float] = (0.0, -9.81, 0.0)
    pin_top_edge: bool = True
    texture_lr: float = 0.01
    seed: int = 1337
    device: str = "auto"

    def validate(self) -> None:
        gh, gw = self.grid_size
        if gh < 4 or gw < 4:
            raise ValueError("grid_size must be at least 4x4")
        if self.simulation_steps <= 0 or self.dt <= 0:
            raise ValueError("invalid simulation parameters")
        if self.mass_density <= 0:
            raise ValueError("mass_density must be positive")
        if self.solver_substeps <= 0:
            raise ValueError("solver_substeps must be positive")


class NativeDifferentiableCloth:
    """Small differentiable mass-spring cloth baseline.

    This is a working native baseline, not a replacement for validated HOOD/DiffCloth integrations.
    It exists so the pipeline has real gradients and CI coverage instead of placeholder physics.
    """

    def __init__(self, config: DifferentiablePhysicsConfig):
        self.config = config
        self.device = resolve_device(config.device)
        self.rest = self._build_grid().to(self.device)
        self.edge_i, self.edge_j, self.edge_rest, self.edge_k = self._build_edges()
        self.pinned = self._build_pins()

    def _build_grid(self) -> torch.Tensor:
        h, w = self.config.grid_size
        yy, xx = torch.meshgrid(torch.linspace(0, 1, h), torch.linspace(0, 1, w), indexing="ij")
        zz = torch.zeros_like(xx)
        return torch.stack((xx - 0.5, 1.0 - yy, zz), dim=-1).reshape(-1, 3)

    def _build_pins(self) -> torch.Tensor:
        h, w = self.config.grid_size
        mask = torch.zeros(h * w, dtype=torch.bool, device=self.device)
        if self.config.pin_top_edge:
            mask[:w] = True
        return mask

    def _build_edges(self):
        h, w = self.config.grid_size
        pairs = []
        ks = []
        for r in range(h):
            for c in range(w):
                idx = r*w + c
                if c+1 < w:
                    pairs.append((idx, idx+1)); ks.append(self.config.structural_stiffness)
                if r+1 < h:
                    pairs.append((idx, idx+w)); ks.append(self.config.structural_stiffness)
                if c+2 < w:
                    pairs.append((idx, idx+2)); ks.append(self.config.bend_stiffness)
                if r+2 < h:
                    pairs.append((idx, idx+2*w)); ks.append(self.config.bend_stiffness)
        ij = torch.tensor(pairs, dtype=torch.long, device=self.device)
        i, j = ij[:,0], ij[:,1]
        rest_len = (self.rest[i] - self.rest[j]).norm(dim=-1)
        k = torch.tensor(ks, dtype=torch.float32, device=self.device)
        return i, j, rest_len, k

    def forces(self, pos: torch.Tensor, vel: torch.Tensor) -> torch.Tensor:
        i, j = self.edge_i, self.edge_j
        delta = pos[j] - pos[i]
        length = delta.norm(dim=-1).clamp_min(1e-8)
        direction = delta / length.unsqueeze(-1)
        magnitude = self.edge_k * (length - self.edge_rest)
        edge_force = magnitude.unsqueeze(-1) * direction
        f = torch.zeros_like(pos)
        f = f.index_add(0, i, edge_force)
        f = f.index_add(0, j, -edge_force)
        gravity = torch.tensor(self.config.gravity, dtype=pos.dtype, device=pos.device)
        mass = self.config.mass_density / pos.shape[0]
        f = f + mass * gravity
        return f

    def simulate(self, external_force: Optional[torch.Tensor] = None) -> dict[str, torch.Tensor]:
        pos = self.rest.clone()
        vel = torch.zeros_like(pos)
        pinned_rest = self.rest[self.pinned]
        mass = self.config.mass_density / pos.shape[0]
        substeps = max(1, int(self.config.solver_substeps))
        sub_dt = self.config.dt / substeps
        damping_factor = torch.exp(torch.tensor(-self.config.damping * sub_dt, dtype=pos.dtype, device=pos.device))
        for _ in range(self.config.simulation_steps):
            for _sub in range(substeps):
                f = self.forces(pos, vel)
                if external_force is not None:
                    f = f + external_force
                acc = f / mass
                # Symplectic Euler with substepping and velocity damping is a stable
                # differentiable baseline for the moderate stiffness used here.
                vel = (vel + sub_dt * acc) * damping_factor
                pos = pos + sub_dt * vel
                if self.pinned.any():
                    # Functional replacement preserves autograd for unpinned vertices.
                    pos = pos.clone(); vel = vel.clone()
                    pos[self.pinned] = pinned_rest
                    vel[self.pinned] = 0
        return {"positions": pos, "velocities": vel}

    def dense_uv_displacement(self, positions: torch.Tensor, resolution: tuple[int,int]) -> torch.Tensor:
        h, w = self.config.grid_size
        disp = (positions[:, :2] - self.rest[:, :2]).reshape(h, w, 2)
        # Normalize xy displacement to image UV scale. x corresponds U; world y is inverted vs image v.
        disp = torch.stack((disp[...,0], -disp[...,1]), dim=-1)
        dense = F.interpolate(disp.permute(2,0,1).unsqueeze(0), size=resolution, mode="bicubic", align_corners=True)
        return dense.permute(0,2,3,1)


class DifferentiableGarmentRenderer:
    def __init__(self, config: DifferentiablePhysicsConfig):
        self.config = config
        self.device = resolve_device(config.device)

    def render(self, texture: torch.Tensor, displacement: torch.Tensor, brightness: float = 1.0) -> torch.Tensor:
        validate_image_tensor(texture)
        b, _, h, w = texture.shape
        if displacement.shape[1:3] != (h,w):
            displacement = F.interpolate(displacement.permute(0,3,1,2), size=(h,w), mode="bilinear", align_corners=True).permute(0,2,3,1)
        if displacement.shape[0] == 1 and b > 1:
            displacement = displacement.expand(b,-1,-1,-1)
        yy, xx = torch.meshgrid(
            torch.linspace(-1,1,h,device=texture.device,dtype=texture.dtype),
            torch.linspace(-1,1,w,device=texture.device,dtype=texture.dtype), indexing="ij")
        grid = torch.stack((xx,yy),dim=-1).unsqueeze(0).expand(b,-1,-1,-1)
        warped = F.grid_sample(texture, grid + 2.0*displacement, mode="bilinear", padding_mode="border", align_corners=True)
        return (warped * brightness).clamp(0,1)


class DifferentiablePhysicsPipeline:
    def __init__(self, config: DifferentiablePhysicsConfig):
        config.validate()
        seed_everything(config.seed)
        self.config = config
        self.device = resolve_device(config.device)
        self.cloth = NativeDifferentiableCloth(config)
        self.renderer = DifferentiableGarmentRenderer(config)
        self.history: list[dict] = []

    def forward(self, texture: torch.Tensor, brightness_values: tuple[float,...] = (0.8,1.0,1.2)) -> dict:
        texture = texture.to(self.device)
        state = self.cloth.simulate()
        dense_disp = self.cloth.dense_uv_displacement(state["positions"], texture.shape[-2:])
        renders = torch.cat([self.renderer.render(texture, dense_disp, b) for b in brightness_values], dim=0)
        return {"renders": renders, "state": state, "displacement": dense_disp}

    def optimize_texture(
        self,
        initial_texture: torch.Tensor,
        evaluator: Callable[[torch.Tensor], torch.Tensor],
        iterations: int = 100,
        tv_weight: float = 0.02,
    ) -> torch.Tensor:
        texture = torch.nn.Parameter(initial_texture.detach().clone().to(self.device).clamp(0,1))
        opt = torch.optim.Adam([texture], lr=self.config.texture_lr)
        for step in range(iterations):
            out = self.forward(texture)
            score = evaluator(out["renders"]).float().mean()
            tv = (texture[:,:,1:]-texture[:,:,:-1]).abs().mean() + (texture[:,:,:,1:]-texture[:,:,:,:-1]).abs().mean()
            loss = score + tv_weight * tv
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_([texture], 5.0)
            opt.step()
            with torch.no_grad(): texture.clamp_(0,1)
            if step % 10 == 0 or step == iterations-1:
                self.history.append({"step":step,"score":float(score.detach().cpu()),"tv":float(tv.detach().cpu()),"loss":float(loss.detach().cpu())})
        return texture.detach()

    def save(self, output_dir: str | Path, texture: Optional[torch.Tensor] = None, name: str = "physics_pipeline") -> Path:
        output_dir = ensure_dir(output_dir)
        path = output_dir / f"{name}.pt"
        torch.save({"config":asdict(self.config),"history":self.history,"texture":None if texture is None else texture.detach().cpu()}, path)
        atomic_json_dump(output_dir / f"{name}.json", {"config":asdict(self.config),"history":self.history})
        return path
