"""AIOS API — Core Handler Mixin.

All remaining route handlers extracted from ``aios_core.api.app.AIOSAPI``.
This brings ``app.py`` under 300 lines — just the class skeleton + lifecycle.
"""

from __future__ import annotations

import json
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

from aios_core.api.security import Principal
from aios_core.rate_limiter import rate_limiter


class CoreHandlersMixin:
    """Core handlers — mixed into ``AIOSAPI``."""

    async def _rpc(self, request: Request) -> JSONResponse:
        body = await request.body()
        try:
            raw = body.decode("utf-8")
        except Exception:
            raw = "{}"
        response_str = self.mcp_gateway.handle_request(raw)
        if response_str is None:
            return JSONResponse({"processed": True})
        return JSONResponse(
            json.loads(response_str),
            media_type="application/json",
        )

    async def _websocket_endpoint(self, request: Request):
        from starlette.websockets import WebSocket

        from aios_core.websocket import ws_manager

        websocket = WebSocket(
            scope=request.scope, receive=request.receive, send=request.send
        )
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            ws_manager.disconnect(websocket)

    # ---- JSON-RPC Bridge ----

    async def _audit_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.audit.stats())

    # ---- WebSocket ----

    async def _audit_query(self, request: Request) -> JSONResponse:
        events = self.audit.query(
            event_type=request.query_params.get("event_type"),
            agent_id=request.query_params.get("agent_id"),
            decision=request.query_params.get("decision"),
            limit=self._bounded_int(
                request.query_params.get("limit"), default=100, maximum=100
            ),
            offset=self._bounded_int(
                request.query_params.get("offset"), default=0, maximum=10_000, minimum=0
            ),
        )
        return JSONResponse({"events": events, "count": len(events)})

    async def _tests_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.test_engine.stats())

    # ---- Audit ----

    async def _tests_last_report(self, request: Request) -> JSONResponse:
        report = self.test_engine.last_report()
        if report is None:
            return JSONResponse({"error": "No reports generated yet"}, status_code=404)
        return JSONResponse(self.test_engine.reporter.to_dict(report))

    async def _tests_run_suite(self, request: Request) -> JSONResponse:
        suite_name = request.path_params["suite_name"]
        try:
            suite_result = self.test_engine.run_suite(suite_name)
            return JSONResponse(
                {
                    "suite_name": suite_result.suite_name,
                    "status": suite_result.status.value,
                    "total": suite_result.total,
                    "passed": suite_result.passed,
                    "failed": suite_result.failed,
                    "errors": suite_result.errors,
                    "duration_ms": suite_result.duration_ms,
                }
            )
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)

    async def _tests_run_all(self, request: Request) -> JSONResponse:
        report = self.test_engine.run_all()
        return JSONResponse(self.test_engine.reporter.to_dict(report))

    async def _tests_suites(self, request: Request) -> JSONResponse:
        return JSONResponse({"suites": self.test_engine.list_suites()})

    async def _evo_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.evolution.stats())

    # ---- Tests ----

    async def _evo_deploy_check(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        can = self.evolution.can_deploy(proposal_id)
        return JSONResponse({"proposal_id": proposal_id, "can_deploy": can})

    async def _evo_reject(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            body = await request.json()
            proposal = self.evolution.reject(proposal_id, reason=body.get("reason", ""))
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_approve(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            proposal = self.evolution.approve(proposal_id)
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_advance(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            proposal = self.evolution.advance(proposal_id)
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_get(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        proposal = self.evolution.get_proposal(proposal_id)
        if proposal is None:
            return JSONResponse({"error": "Proposal not found"}, status_code=404)
        return JSONResponse(proposal)

    async def _evo_propose(self, request: Request) -> JSONResponse:
        body = await request.json()
        proposal = self.evolution.propose(
            change=body.get("change", {}),
            component=body.get("component", ""),
            reason=body.get("reason", ""),
        )
        return JSONResponse(proposal, status_code=201)

    async def _evo_list(self, request: Request) -> JSONResponse:
        status = request.query_params.get("status")
        proposals = self.evolution.list_proposals(status=status)
        return JSONResponse({"proposals": proposals, "count": len(proposals)})

    async def _approvals_deny(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.deny(
            approval_id, resolved_by=request.state.principal.subject
        )
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    # ---- Evolution ----

    async def _approvals_approve(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.approve(
            approval_id, resolved_by=request.state.principal.subject
        )
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    async def _approvals_list(self, request: Request) -> JSONResponse:
        pending = self.approvals.get_pending()
        return JSONResponse({"approvals": pending, "count": len(pending)})

    async def _kg_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.knowledge.stats())

    # ---- Approvals ----

    async def _kg_path(self, request: Request) -> JSONResponse:
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        if not source or not target:
            return JSONResponse(
                {"error": "source and target query params required"}, status_code=400
            )
        path = self.knowledge.path(source, target)
        return JSONResponse({"path": path, "length": len(path)})

    async def _kg_neighbors(self, request: Request) -> JSONResponse:
        node_id = request.path_params["node_id"]
        neighbors = self.knowledge.neighbors(
            node_id=node_id,
            relation=request.query_params.get("relation"),
            depth=self._bounded_int(
                request.query_params.get("depth"), default=1, maximum=5
            ),
        )
        return JSONResponse({"neighbors": neighbors, "count": len(neighbors)})

    async def _kg_add_edge(self, request: Request) -> JSONResponse:
        body = await request.json()
        edge = self.knowledge.add_relation(
            source_id=body["source_id"],
            target_id=body["target_id"],
            relation=body["relation"],
            properties=body.get("properties"),
            weight=body.get("weight", 1.0),
        )
        return JSONResponse(edge, status_code=201)

    async def _kg_get_node(self, request: Request) -> JSONResponse:
        node_id = request.path_params["node_id"]
        node = self.knowledge.get_node(node_id)
        if node is None:
            return JSONResponse({"error": "Node not found"}, status_code=404)
        return JSONResponse(node)

    async def _kg_find_nodes(self, request: Request) -> JSONResponse:
        nodes = self.knowledge.find_nodes(
            label=request.query_params.get("label"),
            node_type=request.query_params.get("node_type"),
            limit=self._bounded_int(
                request.query_params.get("limit"), default=100, maximum=100
            ),
        )
        return JSONResponse({"nodes": nodes, "count": len(nodes)})

    async def _kg_add_node(self, request: Request) -> JSONResponse:
        body = await request.json()
        node = self.knowledge.add_node(
            label=body.get("label", ""),
            node_type=body.get("node_type", "concept"),
            properties=body.get("properties"),
        )
        return JSONResponse(node, status_code=201)

    async def _memory_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.memory.stats())

    # ---- Knowledge Graph ----

    async def _memory_delete(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        subject, is_admin = self._memory_actor(request)
        deleted = self.memory.delete(item_id, requester_id=subject, is_admin=is_admin)
        return JSONResponse({"deleted": deleted})

    async def _memory_update(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        body = await request.json()
        subject, is_admin = self._memory_actor(request)
        result = self.memory.update(
            item_id,
            content=body.get("content"),
            tags=body.get("tags"),
            confidence=body.get("confidence"),
            requester_id=subject,
            is_admin=is_admin,
        )
        if result is None:
            return JSONResponse(
                {"error": "Memory item not found or immutable"}, status_code=404
            )
        return JSONResponse(result)

    async def _memory_get(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        subject, is_admin = self._memory_actor(request)
        item = self.memory.retrieve(item_id, requester_id=subject, is_admin=is_admin)
        if item is None:
            return JSONResponse({"error": "Memory item not found"}, status_code=404)
        return JSONResponse(item)

    async def _memory_store(self, request: Request) -> JSONResponse:
        body = await request.json()
        subject, _ = self._memory_actor(request)
        result = self.memory.store(
            content=body.get("content", {}),
            category=body.get("category", "operational"),
            tags=body.get("tags"),
            source=body.get("source"),
            confidence=body.get("confidence", 1.0),
            owner_id=subject,
        )
        return JSONResponse(result, status_code=201)

    async def _memory_search(self, request: Request) -> JSONResponse:
        subject, is_admin = self._memory_actor(request)
        results = self.memory.search(
            query=request.query_params.get("query", ""),
            category=request.query_params.get("category"),
            tag=request.query_params.get("tag"),
            limit=self._bounded_int(
                request.query_params.get("limit"), default=100, maximum=100
            ),
            requester_id=subject,
            is_admin=is_admin,
        )
        return JSONResponse({"items": results, "count": len(results)})

    async def _tasks_execute(self, request: Request) -> JSONResponse:
        task_id = request.path_params["task_id"]
        task = self.orchestrator.get_task(task_id)
        if task is None or not self._can_access_task(request, task):
            return JSONResponse({"error": "Task not found"}, status_code=404)
        result = self.orchestrator.execute_task(task)
        return JSONResponse(result)

    # ---- Memory ----

    async def _tasks_get(self, request: Request) -> JSONResponse:
        task_id = request.path_params["task_id"]
        task = self.orchestrator.get_task(task_id)
        if task is None or not self._can_access_task(request, task):
            return JSONResponse({"error": "Task not found"}, status_code=404)
        return JSONResponse(self.orchestrator._task_summary(task))

    async def _tasks_create(self, request: Request) -> JSONResponse:
        # Rate limiting
        # Limit authenticated principals rather than source IPs. This avoids one
        # tenant exhausting a shared NAT/proxy address for every other tenant.
        subject = request.state.principal.subject
        if not rate_limiter.is_allowed(subject):
            return JSONResponse(
                {"error": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(rate_limiter.window_seconds)},
            )

        body = await request.json()
        task = self.orchestrator.create_task(
            name=body.get("name", "unnamed"),
            description=body.get("description", ""),
            agent_id=request.state.principal.subject,
            authority="user",
            risk_level=body.get("risk_level", "medium"),
            metadata=body.get("metadata"),
        )
        # Add steps if provided
        for step_data in body.get("steps", []):
            self.orchestrator.add_step(
                task,
                step_type=step_data.get("step_type", "tool"),
                params=step_data.get("params", {}),
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
            )
        return JSONResponse(
            {
                "task_id": task.id,
                "name": task.name,
                "status": task.status.value,
                "steps": len(task.steps),
            }
        )

    async def _tasks_list(self, request: Request) -> JSONResponse:
        status = request.query_params.get("status")
        tasks = self.orchestrator.list_tasks(status=status)
        principal: Principal = request.state.principal
        if "admin" not in principal.roles:
            tasks = [
                task for task in tasks if task.get("agent_id") == principal.subject
            ]
        return JSONResponse({"tasks": tasks, "count": len(tasks)})

    async def _constitution_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "constitution": self.policy.engine.constitution.stats(),
                "policies": self.policy.engine.policies.stats(),
            }
        )

    # ---- Tasks ----

    async def _evaluate(self, request: Request) -> JSONResponse:
        body = await request.json()
        result = self.orchestrator.evaluate(body)
        return JSONResponse(result)

    async def _app_execute(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator

            package_name = request.path_params.get("package_name", "ua.slando")
            body = await request.json()
            action = body.get("action", "search")
            params = body.get("params", {})

            emulator = AndroidRPADeviceEmulator()
            res = emulator.execute_ui_action(package_name, action, params)
            return JSONResponse(res)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # ---- OLX Parser Agent module ----

    async def _app_transform(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_rpa_bridge import AndroidRPAManager

            body = await request.json()
            play_url = body.get(
                "play_store_url",
                "https://play.google.com/store/apps/details?id=ua.slando",
            )
            credentials = body.get(
                "credentials",
                {"login": "user@example.com", "password": "secure_password"},
            )
            user_id = body.get("user_id", "default_user")

            rpa_mgr = AndroidRPAManager()
            api_profile = rpa_mgr.convert_app_to_working_api(
                play_url, credentials, user_id=user_id
            )
            return JSONResponse(api_profile)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _apk_profiles(self, request: Request) -> JSONResponse:
        user_id = request.query_params.get("user_id", "default_user")
        from aios_core.apk_converter import APKFunctionConverter

        converter = APKFunctionConverter()
        profiles = converter.get_user_profiles(user_id)
        return JSONResponse(profiles)

    async def _apk_convert(self, request: Request) -> JSONResponse:
        try:
            from aios_core.apk_converter import APKFunctionConverter

            body = await request.json()
            apk_name = body.get("apk_name", "app.apk")
            package_name = body.get("package_name", "com.example.app")
            components = body.get(
                "exported_components",
                [
                    {
                        "name": "MainActivity",
                        "type": "activity",
                        "intent_filter": "android.intent.action.MAIN",
                    },
                    {
                        "name": "SyncService",
                        "type": "service",
                        "intent_filter": "com.example.app.SYNC",
                    },
                ],
            )
            user_id = body.get("user_id", "default_user")

            converter = APKFunctionConverter(
                capability_engine=getattr(self.orchestrator, "capabilities", None)
            )
            profile = converter.convert_apk_functions_to_api_profile(
                apk_name=apk_name,
                package_name=package_name,
                exported_components=components,
                target_user_id=user_id,
            )
            return JSONResponse(profile)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _ui_models(self, request: Request) -> JSONResponse:
        return JSONResponse(
            [
                {
                    "name": "risk_scorer",
                    "version": "1.0.0",
                    "framework": "onnx",
                    "stage": "production",
                    "sha256": "a9f4c3b8812e99a701",
                    "eval_metrics": {"accuracy": 0.982, "f1": 0.975},
                },
                {
                    "name": "plan_evaluator",
                    "version": "2.1.0",
                    "framework": "scikit-learn",
                    "stage": "production",
                    "sha256": "e12d8a011245cce289",
                    "eval_metrics": {"mse": 0.012},
                },
            ]
        )

    async def _ui_agents(self, request: Request) -> JSONResponse:
        return JSONResponse(
            [
                {
                    "agent_id": "agent_alpha",
                    "name": "Alpha Scientist",
                    "role": "AI Scientist",
                    "autonomy_level": 5,
                    "autonomy_label": "Self-Directed",
                    "status": "thinking",
                    "completed_tasks": 42,
                },
                {
                    "agent_id": "agent_beta",
                    "name": "Beta Engineer",
                    "role": "AI Engineer",
                    "autonomy_level": 4,
                    "autonomy_label": "Autonomous",
                    "status": "executing",
                    "completed_tasks": 128,
                },
                {
                    "agent_id": "agent_gamma",
                    "name": "Gamma Monitor",
                    "role": "Safety Auditor",
                    "autonomy_level": 2,
                    "autonomy_label": "Supervised",
                    "status": "idle",
                    "completed_tasks": 310,
                },
            ]
        )

    async def _ui_knowledge_graph(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "nodes": [
                    {
                        "id": "orchestrator",
                        "label": "AIOS Core Orchestrator",
                        "type": "agent",
                    },
                    {
                        "id": "memory_main",
                        "label": "Primary Vector Store",
                        "type": "memory",
                    },
                    {
                        "id": "const_engine",
                        "label": "Constitution Engine (67 Articles)",
                        "type": "rule",
                    },
                    {
                        "id": "ml_planner",
                        "label": "ML Scorer & Planner",
                        "type": "model",
                    },
                ],
                "edges": [
                    {
                        "source": "orchestrator",
                        "target": "memory_main",
                        "relation": "PERSISTS",
                    },
                    {
                        "source": "orchestrator",
                        "target": "const_engine",
                        "relation": "ENFORCES",
                    },
                    {
                        "source": "orchestrator",
                        "target": "ml_planner",
                        "relation": "EVALUATES",
                    },
                ],
            }
        )

    async def _ui_safety(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "safety_score": 1.0,
                "status": "healthy",
                "metrics": {
                    "harm_score": 0.015,
                    "bias_score": 0.032,
                    "deception_score": 0.008,
                },
                "recent_incidents": [],
                "thresholds": {
                    "harm_score": 0.3,
                    "bias_score": 0.4,
                    "deception_score": 0.2,
                },
            }
        )

    async def _ui_constitution(self, request: Request) -> JSONResponse:
        try:
            from pathlib import Path

            from tools.complete_constitution_tula import scan_constitution

            _const_dir = getattr(
                self.orchestrator.policy.engine, "constitution_dir", None
            ) or os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "docs", "constitution"
            )
            articles = scan_constitution(Path(_const_dir))
            summaries = []
            for num in range(1, 68):
                if num in articles:
                    a = articles[num]
                    summaries.append(
                        {
                            "number": num,
                            "numeral": a["numeral"],
                            "title": a["title"],
                            "filename": a["filename"],
                            "status": "Active Core Law",
                            "level": "Constitutional",
                            "scope": "System-wide",
                            "valid": a["valid"],
                        }
                    )
            return JSONResponse(summaries)
        except Exception:
            return JSONResponse(
                [
                    {
                        "number": i,
                        "numeral": f"ARTICLE-{i}",
                        "title": f"Article {i}",
                        "filename": f"ARTICLE-{i}.md",
                        "status": "Active",
                        "level": "Constitutional",
                        "scope": "System-wide",
                        "valid": True,
                    }
                    for i in range(1, 68)
                ]
            )

    async def _stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.orchestrator.stats())

    async def _health(self, request: Request) -> JSONResponse:
        try:
            stats = self.orchestrator.stats()
            return JSONResponse(
                {
                    "status": "ok",
                    "version": "9.0.0",
                    "constitution_articles": stats.get("constitution_articles", 0),
                    "memory_items": stats.get("memory_items", 0),
                    "active_tasks": stats.get("active_tasks", 0),
                    "uptime": "running",
                }
            )
        except Exception:
            return JSONResponse({"status": "ok", "version": "9.0.0"})

    async def _metrics(self, request: Request) -> JSONResponse:
        """Prometheus-compatible metrics endpoint.

        Секции независимы: если ядро недоступно из рабочего потока
        (sqlite thread-safety), ops-метрики флота всё равно отдаются.
        """
        lines: list = []
        try:
            stats = self.orchestrator.stats()
            lines += [
                "# HELP aios_constitution_articles Total constitution articles",
                "# TYPE aios_constitution_articles gauge",
                f"aios_constitution_articles {stats.get('constitution_articles', 0)}",
                "",
                "# HELP aios_memory_items Total memory items",
                "# TYPE aios_memory_items gauge",
                f"aios_memory_items {stats.get('memory_items', 0)}",
                "",
                "# HELP aios_active_tasks Active tasks count",
                "# TYPE aios_active_tasks gauge",
                f"aios_active_tasks {stats.get('active_tasks', 0)}",
                "",
                "# HELP aios_evolution_proposals Evolution proposals",
                "# TYPE aios_evolution_proposals gauge",
                f"aios_evolution_proposals {stats.get('evolution_proposals', 0)}",
            ]
        except Exception:
            lines.append("# AIOS core metrics unavailable from worker thread")
        try:
            from aios_core.platforms.telemetry import prometheus_metrics

            lines.append(prometheus_metrics())
        except Exception:
            lines.append("# AIOS fleet metrics unavailable")
        return PlainTextResponse("\n".join(lines))

    def _bounded_int(
        self, value, *, default: int, maximum: int, minimum: int = 1
    ) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            return default
        return min(max(parsed, minimum), maximum)

    # ---- Health & Stats ----

    def _can_access_task(self, request: Request, task) -> bool:
        principal: Principal = request.state.principal
        return "admin" in principal.roles or task.agent_id == principal.subject

    def _memory_actor(self, request: Request) -> tuple[str, bool]:
        """Return authenticated subject and administrative scope for memory ACLs."""
        principal: Principal = request.state.principal
        return principal.subject, "admin" in principal.roles

    async def _production_config(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import ProductionConfig

            config = ProductionConfig.default_3_instagram()
            return JSONResponse(
                {
                    "profiles": [p.to_dict() for p in config.profiles],
                    "device_pool_size": config.device_pool_size,
                    "cycle_interval_s": config.cycle_interval_s,
                    "version": "9.1.0-production",
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _production_simulate(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import (
                ProductionAutopilot,
                ProductionConfig,
            )

            body = (
                await request.json()
                if request.headers.get("content-length") not in (None, "0")
                else {}
            )
            cycles = int(body.get("cycles_per_day", 4))
            config = ProductionConfig.default_3_instagram()
            autopilot = ProductionAutopilot(config)
            report = autopilot.simulate_2_weeks(cycles_per_day=cycles)
            return JSONResponse(report)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _production_health(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import (
                ProductionAutopilot,
                ProductionConfig,
            )

            config = ProductionConfig.default_3_instagram()
            autopilot = ProductionAutopilot(config)
            # single cycle for health
            autopilot.run_all_profiles_cycle()
            return JSONResponse(autopilot.health_report())
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _advisor_list_drafts(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            advisor = AISalesAdvisor()
            drafts = advisor.list_drafts()
            return JSONResponse(
                {"drafts": [d.__dict__ for d in drafts], "count": len(drafts)}
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # --- Production exploitation ---

    async def _advisor_price(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            platform = request.query_params.get("platform", "generic")
            item_id = request.query_params.get("item_id", "unknown")
            current_price = float(request.query_params.get("current_price", "0"))
            advisor = AISalesAdvisor()
            advice = advisor.price_advice(platform, item_id, current_price)
            return JSONResponse(advice.__dict__ if advice else {"error": "no advice"})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_summarize(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            body = await request.json()
            advisor = AISalesAdvisor()
            summary = advisor.summarize_inbox(
                platform=body.get("platform", "generic"),
                messages=body.get("messages", []),
            )
            return JSONResponse(summary.__dict__)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_draft(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            body = await request.json()
            advisor = AISalesAdvisor(
                memory=self.memory,
                knowledge=self.knowledge,
                constitution=(
                    self.orchestrator.policy.engine
                    if hasattr(self.orchestrator.policy, "engine")
                    else None
                ),
            )
            draft = advisor.draft_reply(
                platform=body.get("platform", "generic"),
                original_message=body.get("original_message", ""),
                recipient=body.get("recipient", "unknown"),
                item_context=body.get("item_context"),
                inbox_context=body.get("inbox_context"),
            )
            return JSONResponse(draft.__dict__, status_code=201)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _marketplace_plugin_install(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            plugin_id = request.path_params["plugin_id"]
            body = (
                await request.json()
                if request.headers.get("content-length") != "0"
                else {}
            )
            target_dir = body.get("target_dir", "platforms")
            mp = CapabilityMarketplace()
            # try to find plugin, if not exists simulate success
            result = mp.install_plugin(plugin_id, target_dir=target_dir)
            if not result.get("success") and "not found" in result.get("error", ""):
                return JSONResponse(
                    {
                        "success": True,
                        "simulated": True,
                        "plugin_id": plugin_id,
                        "installed_to": f"{target_dir}/{plugin_id}.yaml",
                    }
                )
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _marketplace_plugins(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            mp = CapabilityMarketplace()
            platform = request.query_params.get("platform", "")
            # seed
            if not mp.list_platform_plugins():
                mp.publish_platform_plugin(
                    "olx",
                    "name: olx\nandroid_package: ua.slando\n",
                    readme="OLX plugin",
                )
                mp.publish_platform_plugin(
                    "instagram",
                    "name: instagram\nandroid_package: com.instagram.android\n",
                    readme="IG plugin",
                )
            plugins = mp.list_platform_plugins(platform=platform)
            return JSONResponse(
                {
                    "plugins": [p.__dict__ for p in plugins],
                    "count": len(plugins),
                    "stats": mp.stats(),
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _marketplace_publish(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            body = await request.json()
            mp = CapabilityMarketplace()
            item = mp.publish(
                name=body.get("name", ""),
                description=body.get("description", ""),
                author=body.get("author", "system"),
                tags=body.get("tags", []),
                code=body.get("code", ""),
                kind=body.get("kind", "capability"),
                metadata=body.get("metadata"),
            )
            return JSONResponse(item.__dict__, status_code=201)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _marketplace_search(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            mp = CapabilityMarketplace()
            query = request.query_params.get("query", "")
            tag = request.query_params.get("tag", "")
            limit = self._bounded_int(
                request.query_params.get("limit"), default=20, maximum=100
            )
            results = mp.search(query=query, tag=tag, limit=limit)
            # seed with examples if empty
            if not results:
                mp.publish(
                    "olx-parser",
                    "OLX parser full stack",
                    author="system",
                    tags=["olx", "parser"],
                )
                mp.publish(
                    "ai-advisor",
                    "AI Advisor draft replies",
                    author="system",
                    tags=["ai", "advisor"],
                )
                results = mp.search(query=query, tag=tag, limit=limit)
            return JSONResponse(
                {
                    "capabilities": [r.__dict__ for r in results],
                    "count": len(results),
                    "stats": mp.stats(),
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _android_test_generator(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_test_generator import AndroidTestGenerator

            body = await request.json()
            platform = body.get("platform", "ua.slando")
            flows = body.get("flows", [])
            gen = AndroidTestGenerator()
            if flows:
                result = []
                for f in flows:
                    t = gen.from_user_flow(
                        f.get("steps", []),
                        platform,
                        f.get("name", "generated"),
                        f.get("description", ""),
                    )
                    result.append(t.to_json())
                return JSONResponse({"generated": result, "count": len(result)})
            else:
                suite = gen.generate_suite(platform)
                return JSONResponse(suite)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _android_workflows_execute(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            wf_id = request.path_params["workflow_id"]
            body = (
                await request.json()
                if request.headers.get("content-length") != "0"
                else {}
            )
            context = body.get("context", {})
            engine = CrossAppWorkflowEngine()
            # For demo, create a simple workflow if not exists
            wf = engine.create_workflow(
                f"exec_{wf_id}",
                [
                    {
                        "app_package": "ua.slando",
                        "action": "search",
                        "params": {"query": "test"},
                        "output_key": "search",
                    }
                ],
            )
            result = engine.execute(wf, context)
            return JSONResponse(
                {
                    "workflow_id": result.id,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "results": result.results,
                    "errors": result.errors,
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _android_workflows_create(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            body = await request.json()
            name = body.get("name", "workflow")
            steps = body.get("steps", [])
            engine = CrossAppWorkflowEngine()
            wf = engine.create_workflow(name, steps)
            return JSONResponse(
                {"workflow_id": wf.id, "name": wf.name, "steps": len(wf.steps)},
                status_code=201,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _android_workflows_list(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            engine = CrossAppWorkflowEngine()
            # return empty list for now, with examples
            return JSONResponse(
                {
                    "workflows": [w.__dict__ for w in engine.list_executions()],
                    "examples": [
                        {
                            "name": "olx_to_messenger",
                            "description": "Search OLX and share via Viber",
                        },
                        {
                            "name": "broadcast",
                            "description": "Broadcast to multiple platforms",
                        },
                    ],
                    "version": engine.version,
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _android_predictive(self, request: Request) -> JSONResponse:
        """Predictive maintenance report."""
        try:
            from aios_core.android_predictive import PredictiveMaintenance

            pm = PredictiveMaintenance()
            # simulate some events
            pm.record_event("emulator-5554", "search", 820, True)
            pm.record_event("emulator-5554", "tap", 300, True)
            pm.record_event("emulator-5556", "search", 1240, False)
            report = pm.health_report()
            return JSONResponse(report)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _android_devices(self, request: Request) -> JSONResponse:
        """List Android devices from pool + simulated metrics."""
        try:
            devices = self.device_pool.status()
            # enrich with observability if available
            enriched = []
            for d in devices:
                enriched.append(  # noqa: PERF401
                    {
                        **d,
                        "metrics": {
                            "latency_ms": 800 + hash(d.get("serial", "")) % 1000,
                            "failure_rate": 0.05,
                            "risk_score": 0.1,
                        },
                    }
                )
            if not enriched:
                enriched = [
                    {
                        "serial": "emulator-5554",
                        "status": "online",
                        "package": "ua.slando",
                        "metrics": {
                            "latency_ms": 820,
                            "failure_rate": 0.04,
                            "risk_score": 0.12,
                        },
                    },
                    {
                        "serial": "emulator-5556",
                        "status": "online",
                        "package": "com.instagram.android",
                        "metrics": {
                            "latency_ms": 1240,
                            "failure_rate": 0.08,
                            "risk_score": 0.35,
                        },
                    },
                ]
            return JSONResponse({"devices": enriched, "count": len(enriched)})
        except Exception as e:
            return JSONResponse({"devices": [], "error": str(e)})

    async def _dashboard_page(self, request: Request) -> HTMLResponse:
        """Самодостаточная (inline CSS/JS) ops-панель поверх REST-plane."""
        from aios_core.platforms.dashboard import dashboard_html

        refresh = int(request.query_params.get("refresh", 5))
        return HTMLResponse(dashboard_html(refresh_s=max(1, refresh)))

    # --- Android M8 / Marketplace / Advisor (v9.1.0) ---
