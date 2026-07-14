"""Task scheduler — assigns tasks to the best available agent."""

from __future__ import annotations

import logging
from typing import Any

from rubric.models.story import Task
from rubric.models.agent import Agent, STAGE_RESPONSIBILITIES

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Assigns tasks to agents based on role, availability, and workload balancing.

    Strategy:
    1. Filter agents by required role (if specified)
    2. Filter by availability (not at max concurrent tasks)
    3. Rank by utilization (prefer less busy agents for load balancing)
    4. Pick the best candidate
    """

    def find_best_agent(
        self,
        task: Task,
        agents: list[Agent],
        stage: str | None = None,
    ) -> Agent | None:
        """Find the best agent to handle a task."""
        # Determine effective role requirement
        required_role = task.required_role
        if not required_role and stage:
            # Use stage responsibilities as hint
            stage_roles = STAGE_RESPONSIBILITIES.get(stage, [])
            if len(stage_roles) == 1:
                required_role = stage_roles[0].value

        # Filter candidates
        candidates = [a for a in agents if a.available and a.can_handle(required_role)]

        if not candidates:
            # Try without role filter — any available agent
            candidates = [a for a in agents if a.available]

        if not candidates:
            logger.debug(f"No available agent for task '{task.title}'")
            return None

        # Rank: prefer matching role, then lower utilization
        def rank(agent: Agent) -> tuple[int, float]:
            role_match = 0 if agent.can_handle(task.required_role) else 1
            return (role_match, agent.utilization)

        candidates.sort(key=rank)
        return candidates[0]

    def assign_task(self, task: Task, agent: Agent) -> None:
        """Assign a task to an agent and update both sides."""
        agent.pick_up_task(task.id)
        task.assign(agent.id)
        logger.info(
            f"Assigned '{task.title}' -> {agent.name} "
            f"(utilization: {agent.utilization:.0%})"
        )

    def get_workload(self, agents: list[Agent]) -> dict[str, Any]:
        """Return a snapshot of agent workload."""
        return {
            agent.name: {
                "role": agent.role.value,
                "active_tasks": len(agent.active_tasks),
                "completed_tasks": agent.completed_tasks,
                "utilization": f"{agent.utilization:.0%}",
                "available": agent.available,
            }
            for agent in agents
        }
