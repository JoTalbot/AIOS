"""Planner abstraction for AIOS intelligence layer."""

from abc import ABC, abstractmethod


class PlannerInterface(ABC):
    @abstractmethod
    async def create_plan(self, goal):
        raise NotImplementedError

    @abstractmethod
    async def validate_plan(self, plan):
        raise NotImplementedError

    @abstractmethod
    async def update_plan(self, plan, feedback):
        raise NotImplementedError
