class Orchestrator:
    """Central coordination engine for AIOS.

    Plans and executes multi-step tasks, coordinating all subsystems.
    Every step goes through constitutional evaluation before execution.

    Usage:
        orch = Orchestrator(db=Database(":memory:"), constitution_dir="...", policies_dir="...")

        # Create and execute a task
        task = orch.create_task("analyze_data", "Analyze user data patterns", risk_level="low")
        orch.add_step(task, "evaluate", params={"goal": "Read metrics", ...})
        orch.add_step(task, "memory", params={"action": "store", "content": {...}, "category": "operational"})
        result = orch.execute_task(task)
    """