"""AIOS Route Registration.

All Starlette Route objects defined here.  Handler methods live on the
``AIOSAPI`` class in ``aios_core.api.app``.

Extracted to keep ``app.py`` under 500 lines.
"""

from starlette.routing import Route, WebSocketRoute


def register_routes(api) -> list:
    """Return the full list of Starlette Route objects for *api*."""
    return [
            Route("/health", api._health),
            Route("/metrics", api._metrics),
            # Stats & Web UI endpoints
            Route("/api/v1/stats", api._stats),
            Route("/api/v1/constitution", api._ui_constitution),
            Route("/api/v1/safety", api._ui_safety),
            Route("/api/v1/knowledge-graph", api._ui_knowledge_graph),
            Route("/api/v1/agents", api._ui_agents),
            Route("/api/v1/models", api._ui_models),
            Route("/api/v1/apk/convert", api._apk_convert, methods=["POST"]),
            Route("/api/v1/apk/profiles", api._apk_profiles, methods=["GET"]),
            Route("/api/v1/apps/transform", api._app_transform, methods=["POST"]),
            Route(
                "/api/v1/apps/{package_name}/execute",
                self._app_execute,
                methods=["POST"],
            ),
            # OLX Parser Agent module
            Route("/api/v1/modules/olx/ads", api._olx_ads, methods=["GET"]),
            Route("/api/v1/modules/olx/stats", api._olx_stats, methods=["GET"]),
            Route("/api/v1/modules/olx/history", api._olx_history, methods=["GET"]),
            Route("/api/v1/modules/olx/drops", api._olx_drops, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/recommendations",
                self._olx_recommend,
                methods=["POST"],
            ),
            Route("/api/v1/modules/olx/collect", api._olx_collect, methods=["POST"]),
            Route("/api/v1/modules/olx/schedule", api._olx_schedule, methods=["POST"]),
            Route("/api/v1/modules/olx/schedule", api._olx_unschedule, methods=["DELETE"]),
            Route("/api/v1/modules/olx/detail", api._olx_detail_parse, methods=["POST"]),
            Route("/api/v1/modules/olx/chats", api._olx_chats, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/chats/reply",
                self._olx_chat_reply,
                methods=["POST"],
            ),
            Route("/api/v1/modules/olx/outbox", api._olx_outbox, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/outbox/send",
                self._olx_outbox_send,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/outbox/cancel",
                self._olx_outbox_cancel,
                methods=["POST"],
            ),
            Route("/api/v1/modules/olx/own", api._olx_own_list, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/own/snapshot",
                self._olx_own_snapshot,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/own/stagnant",
                self._olx_own_stagnant,
                methods=["GET"],
            ),
            Route(
                "/api/v1/modules/olx/own/improve",
                self._olx_own_improve,
                methods=["POST"],
            ),
            Route("/api/v1/modules/olx/own/repost", api._olx_own_repost, methods=["POST"]),
            Route("/api/v1/modules/olx/own/edit", api._olx_own_edit, methods=["POST"]),
            Route("/api/v1/modules/olx/notify", api._olx_notify, methods=["POST"]),
            Route(
                "/api/v1/modules/olx/subscriptions",
                self._olx_subscriptions,
                methods=["GET"],
            ),
            Route(
                "/api/v1/modules/olx/subscriptions",
                self._olx_subscription_add,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/subscriptions/check",
                self._olx_subscription_check,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/subscriptions/{subscription_id:int}",
                self._olx_subscription_remove,
                methods=["DELETE"],
            ),
            Route("/api/v1/modules/olx/favorites", api._olx_favorites, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/favorites",
                self._olx_favorite_add,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/favorites/alerts",
                self._olx_favorite_alerts,
                methods=["GET"],
            ),
            Route(
                "/api/v1/modules/olx/favorites/{fingerprint}",
                self._olx_favorite_remove,
                methods=["DELETE"],
            ),
            Route("/api/v1/modules/olx/autowatch", api._olx_autowatch, methods=["POST"]),
            Route("/api/v1/modules/olx/doctor", api._olx_doctor, methods=["GET"]),
            Route("/api/v1/modules/olx/profile", api._olx_profile, methods=["GET"]),
            Route(
                "/api/v1/modules/olx/profile/parse",
                self._olx_profile_parse,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/profile/edit",
                self._olx_profile_edit,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/competitive",
                self._olx_competitive,
                methods=["GET"],
            ),
            Route(
                "/api/v1/modules/olx/competitive/refresh",
                self._olx_competitive_refresh,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/olx/competitive/seller-scan",
                self._olx_competitive_seller_scan,
                methods=["POST"],
            ),
            Route("/api/v1/platforms", api._platforms_list, methods=["GET"]),
            Route(
                "/api/v1/platforms/{platform}/hints",
                self._platform_hints,
                methods=["POST"],
            ),
            Route("/api/v1/profiles", api._profiles_list, methods=["GET"]),
            Route("/api/v1/profiles", api._profiles_create, methods=["POST"]),
            Route(
                "/api/v1/profiles/{platform}/{name}",
                self._profiles_show,
                methods=["GET"],
            ),
            Route(
                "/api/v1/profiles/{platform}/{name}",
                self._profiles_remove,
                methods=["DELETE"],
            ),
            Route(
                "/api/v1/profiles/{platform}/default",
                self._profiles_set_default,
                methods=["POST"],
            ),
            Route("/api/v1/devices", api._devices_list, methods=["GET"]),
            Route("/api/v1/devices/register", api._devices_register, methods=["POST"]),
            Route("/api/v1/devices/lease", api._devices_lease, methods=["POST"]),
            Route("/api/v1/devices/release", api._devices_release, methods=["POST"]),
            Route("/api/v1/devices/heartbeat", api._devices_heartbeat, methods=["POST"]),
            Route("/api/v1/devices/reap", api._devices_reap, methods=["POST"]),
            Route("/api/v1/devices/limits", api._devices_limits_get, methods=["GET"]),
            Route("/api/v1/devices/limits", api._devices_limits_set, methods=["POST"]),
            Route("/api/v1/devices/waitlist", api._devices_waitlist, methods=["GET"]),
            Route(
                "/api/v1/devices/waitlist/cancel",
                self._devices_waitlist_cancel,
                methods=["POST"],
            ),
            Route("/api/v1/shards", api._shards_list, methods=["GET"]),
            Route("/api/v1/shards", api._shards_add, methods=["POST"]),
            Route("/api/v1/shards/route", api._shards_route, methods=["POST"]),
            Route("/api/v1/shards/route", api._shards_unroute, methods=["DELETE"]),
            Route("/api/v1/shards/gateway", api._shards_gateway, methods=["POST"]),
            Route("/api/v1/shards/{host}", api._shards_remove, methods=["DELETE"]),
            Route("/api/v1/shards/jobs", api._shard_jobs_list, methods=["GET"]),
            Route("/api/v1/shards/jobs", api._shard_jobs_enqueue, methods=["POST"]),
            Route("/api/v1/shards/stats", api._shard_jobs_stats, methods=["GET"]),
            # Android M8 + Marketplace + AI Advisor (v9.1.0)
            Route("/api/v1/android/devices", api._android_devices, methods=["GET"]),
            Route("/api/v1/android/predictive", api._android_predictive, methods=["GET"]),
            Route(
                "/api/v1/android/workflows",
                self._android_workflows_list,
                methods=["GET"],
            ),
            Route(
                "/api/v1/android/workflows",
                self._android_workflows_create,
                methods=["POST"],
            ),
            Route(
                "/api/v1/android/workflows/{workflow_id}/execute",
                self._android_workflows_execute,
                methods=["POST"],
            ),
            Route(
                "/api/v1/android/test-generator",
                self._android_test_generator,
                methods=["POST"],
            ),
            Route("/api/v1/marketplace/search", api._marketplace_search, methods=["GET"]),
            Route(
                "/api/v1/marketplace/publish",
                self._marketplace_publish,
                methods=["POST"],
            ),
            Route(
                "/api/v1/marketplace/plugins",
                self._marketplace_plugins,
                methods=["GET"],
            ),
            Route(
                "/api/v1/marketplace/plugins/{plugin_id}/install",
                self._marketplace_plugin_install,
                methods=["POST"],
            ),
            Route("/api/v1/advisor/draft", api._advisor_draft, methods=["POST"]),
            Route("/api/v1/advisor/summarize", api._advisor_summarize, methods=["POST"]),
            Route("/api/v1/advisor/price", api._advisor_price, methods=["GET"]),
            Route("/api/v1/advisor/drafts", api._advisor_list_drafts, methods=["GET"]),
            # Production exploitation
            Route("/api/v1/production/health", api._production_health, methods=["GET"]),
            Route(
                "/api/v1/production/simulate",
                self._production_simulate,
                methods=["POST"],
            ),
            Route("/api/v1/production/config", api._production_config, methods=["GET"]),
            Route("/dashboard", api._dashboard_page, methods=["GET"]),
            # Generic platform module surfaces (descriptor-driven). Статичные
            # роуты olx зарегистрированы выше и матчатся первыми.
            Route("/api/v1/modules/{platform}/ads", api._module_ads, methods=["GET"]),
            Route(
                "/api/v1/modules/{platform}/ads/ingest",
                self._module_ads_ingest,
                methods=["POST"],
            ),
            Route("/api/v1/modules/{platform}/stats", api._module_stats, methods=["GET"]),
            Route(
                "/api/v1/modules/{platform}/ads/{fingerprint}/history",
                self._module_history,
                methods=["GET"],
            ),
            Route("/api/v1/modules/{platform}/own", api._module_own, methods=["GET"]),
            Route(
                "/api/v1/modules/{platform}/own/snapshot",
                self._module_own_snapshot,
                methods=["POST"],
            ),
            Route("/api/v1/modules/{platform}/chats", api._module_chats, methods=["GET"]),
            Route(
                "/api/v1/modules/{platform}/outbox",
                self._module_outbox,
                methods=["GET"],
            ),
            Route(
                "/api/v1/modules/{platform}/outbox/send",
                self._module_outbox_send,
                methods=["POST"],
            ),
            Route(
                "/api/v1/modules/{platform}/outbox/flush",
                self._module_outbox_flush,
                methods=["POST"],
            ),
            Route("/api/v1/modules/olx/advisor", api._olx_advisor, methods=["GET"]),
            # Constitutional evaluation
            Route("/api/v1/evaluate", api._evaluate, methods=["POST"]),
            Route("/api/v1/constitution/stats", api._constitution_stats),
            # Tasks
            Route("/api/v1/tasks", api._tasks_list, methods=["GET"]),
            Route("/api/v1/tasks", api._tasks_create, methods=["POST"]),
            Route("/api/v1/tasks/{task_id}", api._tasks_get),
            Route("/api/v1/tasks/{task_id}/execute", api._tasks_execute, methods=["POST"]),
            # Memory (stats route must come before {item_id} to avoid capture)
            Route("/api/v1/memory", api._memory_search, methods=["GET"]),
            Route("/api/v1/memory", api._memory_store, methods=["POST"]),
            Route("/api/v1/memory/stats", api._memory_stats),
            Route("/api/v1/memory/{item_id}", api._memory_get),
            Route("/api/v1/memory/{item_id}", api._memory_update, methods=["PUT"]),
            Route("/api/v1/memory/{item_id}", api._memory_delete, methods=["DELETE"]),
            # Knowledge
            Route("/api/v1/knowledge/nodes", api._kg_add_node, methods=["POST"]),
            Route("/api/v1/knowledge/nodes", api._kg_find_nodes, methods=["GET"]),
            Route("/api/v1/knowledge/nodes/{node_id}", api._kg_get_node),
            Route("/api/v1/knowledge/edges", api._kg_add_edge, methods=["POST"]),
            Route("/api/v1/knowledge/nodes/{node_id}/neighbors", api._kg_neighbors),
            Route("/api/v1/knowledge/path", api._kg_path),
            Route("/api/v1/knowledge/stats", api._kg_stats),
            # Approvals
            Route("/api/v1/approvals", api._approvals_list),
            Route(
                "/api/v1/approvals/{approval_id}/approve",
                self._approvals_approve,
                methods=["POST"],
            ),
            Route(
                "/api/v1/approvals/{approval_id}/deny",
                self._approvals_deny,
                methods=["POST"],
            ),
            # Evolution
            Route("/api/v1/evolution/proposals", api._evo_list),
            Route("/api/v1/evolution/proposals", api._evo_propose, methods=["POST"]),
            Route("/api/v1/evolution/proposals/{proposal_id}", api._evo_get),
            Route(
                "/api/v1/evolution/proposals/{proposal_id}/advance",
                self._evo_advance,
                methods=["POST"],
            ),
            Route(
                "/api/v1/evolution/proposals/{proposal_id}/approve",
                self._evo_approve,
                methods=["POST"],
            ),
            Route(
                "/api/v1/evolution/proposals/{proposal_id}/reject",
                self._evo_reject,
                methods=["POST"],
            ),
            Route(
                "/api/v1/evolution/proposals/{proposal_id}/deploy-check",
                self._evo_deploy_check,
            ),
            Route("/api/v1/evolution/stats", api._evo_stats),
            # Tests
            Route("/api/v1/tests/suites", api._tests_suites),
            Route("/api/v1/tests/run", api._tests_run_all, methods=["POST"]),
            Route(
                "/api/v1/tests/run/{suite_name}",
                self._tests_run_suite,
                methods=["POST"],
            ),
            Route("/api/v1/tests/last-report", api._tests_last_report),
            Route("/api/v1/tests/stats", api._tests_stats),
            # Audit
            Route("/api/v1/audit", api._audit_query),
            Route("/api/v1/audit/stats", api._audit_stats),
            # JSON-RPC bridge
            Route("/rpc", api._rpc, methods=["POST"]),
            # WebSocket (real-time)
            WebSocketRoute("/ws", api._websocket_endpoint),
        ]

