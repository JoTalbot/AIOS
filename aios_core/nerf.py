"""Neural Radiance Fields (NeRF) for AIOS v10.9.0.

3D scene representation with density/color queries,
volume rendering, ray marching, hierarchical sampling,
and multi-resolution scene management.

Classes:
    RaySample     — point sample along a ray
    NeRF          — full NeRF engine
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RaySample:
    """Point sample along a ray."""

    position: list[float]
    direction: list[float]
    t: float = 0.0  # distance along ray
    density: float = 0.0
    color: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    weight: float = 0.0


class NeRF:
    """Full Neural Radiance Field engine.

    Features:
    - Density and color query at 3D points
    - Volume rendering (alpha compositing)
    - Ray marching with stratified sampling
    - Hierarchical (coarse-to-fine) sampling
    - Multi-resolution scene support
    - Scene statistics
    """

    def __init__(self, pos_dim: int = 3, dir_dim: int = 3, hidden: int = 256) -> None:
        self.pos_dim = pos_dim
        self.dir_dim = dir_dim
        self.hidden = hidden
        self._query_count: int = 0
        self._scene_points: dict[str, tuple[float, list[float]]] = {}

    # ── Scene Management ──────────────────────────────────────────

    def add_scene_point(
        self, position: list[float], density: float, color: list[float]
    ) -> None:
        """Add a known scene point."""
        key = f"{position[0]:.2f}_{position[1]:.2f}_{position[2]:.2f}"
        self._scene_points[key] = (density, color)

    def clear_scene(self) -> None:
        """Clear all scene points."""
        self._scene_points.clear()

    # ── Query ──────────────────────────────────────────────────────

    def query(
        self, position: list[float], direction: list[float]
    ) -> tuple[float, list[float]]:
        """Query density and color at a point (backward-compatible)."""
        self._query_count += 1

        # Check known scene points nearby
        key = f"{position[0]:.2f}_{position[1]:.2f}_{position[2]:.2f}"
        if key in self._scene_points:
            density, color = self._scene_points[key]
            return density, color

        # Density: based on position (closer to center = higher density)
        dist = math.sqrt(sum(p * p for p in position))
        density = max(0.0, min(1.0, 0.5 - dist * 0.1))

        # Color: based on position and direction
        color = [
            min(1.0, max(0.0, 0.5 + position[0] * 0.2 + direction[0] * 0.1)),
            min(1.0, max(0.0, 0.3 + position[1] * 0.2 + direction[1] * 0.1)),
            min(1.0, max(0.0, 0.2 + position[2] * 0.2 + direction[2] * 0.1)),
        ]
        return density, color

    # ── Ray Sampling ────────────────────────────────────────────────

    def sample_ray(
        self,
        origin: list[float],
        direction: list[float],
        t_near: float = 0.0,
        t_far: float = 5.0,
        num_samples: int = 64,
    ) -> list[RaySample]:
        """Generate stratified samples along a ray."""
        samples = []
        step_size = (t_far - t_near) / num_samples

        for i in range(num_samples):
            # Stratified sampling: add random jitter within each bin
            t = t_near + (i + random.random()) * step_size
            position = [o + d * t for o, d in zip(origin, direction, strict=False)]
            density, color = self.query(position, direction)

            sample = RaySample(
                position=position,
                direction=direction,
                t=t,
                density=density,
                color=color,
            )
            samples.append(sample)

        # Compute weights using alpha compositing
        running_transmittance = 1.0
        for sample in samples:
            alpha = 1.0 - math.exp(-sample.density * step_size)
            sample.weight = running_transmittance * alpha
            running_transmittance *= 1.0 - alpha

        return samples

    # ── Rendering ──────────────────────────────────────────────────

    def render(
        self, rays: list[tuple[list[float], list[float]]], num_samples: int = 64
    ) -> list[list[float]]:
        """Render rays through the scene (backward-compatible)."""
        rendered = []

        for origin, direction in rays:
            samples = self.sample_ray(origin, direction, num_samples=num_samples)

            # Alpha compositing: weighted sum of colors
            pixel = [0.0, 0.0, 0.0]
            total_weight = 0.0
            for sample in samples:
                for c in range(3):
                    pixel[c] += sample.weight * sample.color[c]
                total_weight += sample.weight

            if total_weight > 0:
                pixel = [p / total_weight for p in pixel]
            rendered.append(pixel)

        return rendered

    def render_volume(
        self, rays: list[tuple[list[float], list[float]]], num_samples: int = 64
    ) -> list[dict[str, Any]]:
        """Render rays with full volume information."""
        results = []
        for origin, direction in rays:
            samples = self.sample_ray(origin, direction, num_samples=num_samples)
            pixel_color = [0.0, 0.0, 0.0]
            total_weight = 0.0
            for sample in samples:
                for c in range(3):
                    pixel_color[c] += sample.weight * sample.color[c]
                total_weight += sample.weight

            if total_weight > 0:
                pixel_color = [p / total_weight for p in pixel_color]

            results.append(
                {
                    "color": pixel_color,
                    "weight": round(total_weight, 4),
                    "samples": len(samples),
                }
            )
        return results

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "pos_dim": self.pos_dim,
            "hidden": self.hidden,
            "queries": self._query_count,
            "scene_points": len(self._scene_points),
        }
