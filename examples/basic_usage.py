"""Basic AIOS Usage Example"""

from aios_core import Orchestrator, Database


def main():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    # Create and execute a task
    task = orch.create_task("example", "Demonstration task")
    orch.add_step(task, "memory", {"action": "store", "content": {"hello": "world"}})
    orch.add_step(task, "reason", {"question": "What was stored?"})

    result = orch.execute_task(task)
    print("Task completed:", result["status"])

    # Check stats
    stats = orch.stats()
    print("Total tasks:", stats["total_tasks"])


if __name__ == "__main__":
    main()
