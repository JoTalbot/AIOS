"""Embodied AI and Robotics Interface for AIOS v10.10.0.

Embodied AI: robot interface with sensor/actuator management,
sensor fusion, path planning, obstacle avoidance, action
primitives, proprioception, and multi-robot coordination.

Classes:
    SensorReading  — timestamped sensor data
    RobotInterface — single robot controller
    EmbodiedAI     — multi-robot coordination engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Timestamped sensor data."""

    sensor_type: str
    value: float
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0


class RobotInterface:
    """Interface to physical or simulated robots."""

    def __init__(self, robot_id: str) -> None:
        self.robot_id = robot_id
        self.sensors: dict[str, SensorReading] = {}
        self.actuators: dict[str, float] = {}
        self._position: dict[str, float] = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._orientation: dict[str, float] = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        self._velocity: float = 0.0
        self._obstacles: list[dict[str, float]] = []

    def read_sensor(self, sensor: str) -> SensorReading:
        """Read sensor data (backward-compatible + enhanced)."""
        # Generate simulated sensor reading
        value = random.uniform(0, 100)
        reading = SensorReading(
            sensor_type=sensor, value=value, confidence=random.uniform(0.8, 1.0)
        )
        self.sensors[sensor] = reading
        return reading

    def actuate(self, actuator: str, value: float) -> None:
        """Actuate a mechanism (backward-compatible)."""
        self.actuators[actuator] = value
        # Update position based on actuation
        if actuator == "wheel_left":
            self._position["x"] += value * 0.1
        elif actuator == "wheel_right":
            self._position["y"] += value * 0.1

    def sensor_fusion(self) -> dict[str, float]:
        """Fuse all sensor readings into a unified perception."""
        fused: dict[str, float] = {}
        total_conf = 0.0
        for sensor_type, reading in self.sensors.items():
            fused[sensor_type] = reading.value * reading.confidence
            total_conf += reading.confidence
        if total_conf > 0:
            fused["confidence_avg"] = total_conf / len(self.sensors)
        return fused

    def sense_obstacles(self) -> list[dict[str, float]]:
        """Detect obstacles in environment."""
        self._obstacles = [
            {
                "x": random.uniform(-5, 5),
                "y": random.uniform(-5, 5),
                "size": random.uniform(0.5, 2.0),
            }
            for _ in range(random.randint(1, 5))
        ]
        return self._obstacles

    def avoid_obstacle(self, obstacle: dict[str, float]) -> dict[str, float]:
        """Compute avoidance action for an obstacle."""
        dx = obstacle["x"] - self._position["x"]
        dy = obstacle["y"] - self._position["y"]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < obstacle["size"] * 2:
            # Move away from obstacle
            return {"wheel_left": -dx / dist, "wheel_right": -dy / dist}
        return {"wheel_left": 0.0, "wheel_right": 0.0}

    def get_position(self) -> dict[str, float]:
        """Get current position."""
        return dict(self._position)

    def get_proprioception(self) -> dict[str, Any]:
        """Get proprioceptive feedback."""
        return {
            "position": self._position,
            "orientation": self._orientation,
            "velocity": self._velocity,
            "actuator_states": dict(self.actuators),
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "robot": self.robot_id,
            "sensors": len(self.sensors),
            "actuators": len(self.actuators),
        }


class EmbodiedAI:
    """Embodied intelligence system."""

    def __init__(self) -> None:
        self.robots: dict[str, RobotInterface] = {}
        self._task_queue: list[dict[str, Any]] = []

    def register_robot(self, robot_id: str) -> RobotInterface:
        """Register a robot (backward-compatible)."""
        robot = RobotInterface(robot_id)
        self.robots[robot_id] = robot
        logger.info("Registered robot %s", robot_id)
        return robot

    def assign_task(self, robot_id: str, task: dict[str, Any]) -> bool:
        """Assign a task to a robot."""
        if robot_id in self.robots:
            self._task_queue.append({"robot_id": robot_id, "task": task})
            return True
        return False

    def coordinate(self) -> dict[str, Any]:
        """Coordinate all robots for shared tasks."""
        positions = {rid: r.get_position() for rid, r in self.robots.items()}
        return {
            "robots": len(self.robots),
            "positions": positions,
            "pending_tasks": len(self._task_queue),
        }

    def path_plan(
        self, robot_id: str, goal: dict[str, float]
    ) -> list[dict[str, float]]:
        """Simple path planning: straight line waypoints."""
        if robot_id not in self.robots:
            return []
        robot = self.robots[robot_id]
        start = robot.get_position()
        steps = 10
        waypoints: list[dict[str, float]] = []
        for i in range(steps):
            t = (i + 1) / steps
            wp = {k: start.get(k, 0) * (1 - t) + goal.get(k, 0) * t for k in goal}
            waypoints.append(wp)
        return waypoints

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {"robots": len(self.robots), "pending_tasks": len(self._task_queue)}
