"""AIOS API — OLX Handler Mixin.

Contains all OLX Parser Agent endpoint handlers extracted from
``aios_core.api.app.AIOSAPI`` to keep the main class under 2000 lines.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

# The mixin accesses ``self.db``, ``self.orchestrator``, etc. which are
# provided by the ``AIOSAPI`` base class at runtime.
# pylint: disable=no-member


class OLXHandlersMixin:
    """OLX route handlers — mixed into ``AIOSAPI``."""

    async def _olx_unschedule(self, request: Request) -> JSONResponse:
        """Stop the periodic background collection."""
        scheduler = self._olx_get_scheduler()
        was_running = scheduler.running
        scheduler.stop()
        return JSONResponse(
            {
                "scheduled": False,
                "was_running": was_running,
                "history": scheduler.history[-20:],
            }
        )

    # ---- Evaluate ----

    async def _olx_schedule(self, request: Request) -> JSONResponse:
        """Start periodic background collection."""
        try:
            body = await request.json()
            queries = body.get("queries")
            if not isinstance(queries, list) or not queries:
                queries = [body.get("query") or "olx"]
            interval_s = float(body.get("interval_s", 3600.0))
            if interval_s < 10.0:
                return JSONResponse(
                    {"error": "interval_s must be at least 10 seconds"},
                    status_code=400,
                )
            max_cards = self._bounded_int(body.get("max_cards"), default=50, maximum=500)
            scheduler = self._olx_get_scheduler(interval_s)
            started = scheduler.start(queries, max_cards=max_cards)
            return JSONResponse(
                {
                    "scheduled": scheduler.running,
                    "started_now": started,
                    "queries": queries,
                    "interval_s": scheduler.interval_s,
                    "max_cards": max_cards,
                }
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_collect(self, request: Request) -> JSONResponse:
        """Run a one-off ADB collection for one or more search queries."""
        try:
            body = await request.json()
            queries = body.get("queries")
            if not isinstance(queries, list) or not queries:
                queries = [body.get("query") or "olx"]
            max_cards = self._bounded_int(body.get("max_cards"), default=50, maximum=500)
            scheduler = self._olx_get_scheduler()
            summaries = scheduler.run_once(queries, max_cards=max_cards)
            return JSONResponse({"summaries": summaries})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_recommend(self, request: Request) -> JSONResponse:
        """Generate listing advice from collected competitors."""
        try:
            from dataclasses import asdict

            from aios_core.modules.olx import AdCard, RecommendationEngine

            body = await request.json()
            query = body.get("query")
            ads = self._olx_db(request).get_ads(query=query)
            my_ad = None
            if body.get("title") is not None or body.get("price") is not None:
                my_ad = AdCard(
                    title=body.get("title") or "",
                    price=body.get("price"),
                    currency=body.get("currency", "UAH"),
                    query=query,
                )
            advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
            payload = asdict(advice)
            payload["text"] = advice.to_text()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_stats(self, request: Request) -> JSONResponse:
        """Competitor market statistics for a search query (or the whole store)."""
        from aios_core.modules.olx import CompetitorAnalyzer

        query = request.query_params.get("query")
        ads = self._olx_db(request).get_ads(query=query)
        report = CompetitorAnalyzer().analyze(ads, query=query)
        return JSONResponse(report.to_dict())

    async def _olx_ads(self, request: Request) -> JSONResponse:
        """List collected OLX ads (`query` filter, bounded `limit`)."""
        query = request.query_params.get("query")
        limit = self._bounded_int(request.query_params.get("limit"), default=100, maximum=1000)
        ads = self._olx_db(request).get_ads(query=query, limit=limit)
        return JSONResponse(
            {
                "count": len(ads),
                "total": self._olx_db(request).count(query=query),
                "items": [ad.to_dict() for ad in ads],
            }
        )

    def _olx_get_scheduler(self, interval_s: float = 3600.0):
        # Фоновый планировщик — API-wide синглтон: работает на дефолтном
        # хранилище. Per-profile фоновые сборы запускаются через CLI/cron
        # с --profile (см. docs/PLATFORMS_SCALING.md).
        if self._olx_scheduler is None:
            from aios_core.modules.olx import CollectionScheduler

            self._olx_scheduler = CollectionScheduler(
                collector=self.olx_collector,
                storage=self.olx_storage,
                interval_s=interval_s,
            )
        self._olx_scheduler.interval_s = float(interval_s)
        return self._olx_scheduler

    async def _olx_advisor(self, request: Request) -> JSONResponse:
        """Portfolio advice: actions for own ads + new-listing suggestions."""
        from typing import Dict

        from aios_core.modules.olx import StrategyAdvisor

        advisor = StrategyAdvisor(self._olx_db(request))
        actions = [item.to_dict() for item in advisor.advise_actions()]
        payload: Dict[str, object] = {"actions": actions}
        if request.query_params.get("new") == "1":
            payload["new_listings"] = [item.to_dict() for item in advisor.advise_new_listings()]
        return JSONResponse(payload)

    async def _olx_competitive(self, request: Request) -> JSONResponse:
        """Competitive report for one own listing (`fingerprint` required)."""
        from aios_core.modules.olx import CompetitiveWatch

        fingerprint = request.query_params.get("fingerprint")
        if not fingerprint:
            return JSONResponse(
                {"error": "query parameter 'fingerprint' is required"}, status_code=400
            )
        report = CompetitiveWatch(self._olx_db(request)).report(fingerprint)
        return JSONResponse(report)

    async def _olx_competitive_seller_scan(self, request: Request) -> JSONResponse:
        """Crawl a competitor's portfolio from a detail-page UI dump.

        Body: ``{"fingerprint": <own ad fp>, "xml": "<hierarchy ...>"}``.
        """
        try:
            from aios_core.modules.olx import CompetitiveWatch, OwnAd

            body = await request.json()
            fingerprint = body.get("fingerprint")
            xml = body.get("xml")
            if not fingerprint or not xml:
                return JSONResponse(
                    {"error": "body must contain 'fingerprint' and 'xml'"},
                    status_code=400,
                )
            rows = [
                row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint
            ]
            if not rows:
                return JSONResponse({"error": f"own ad '{fingerprint}' not found"}, status_code=404)
            row = rows[0]
            own = OwnAd(
                title=row["title"],
                price=row["price"],
                currency=row["currency"],
                views=row["last_views"] or 0,
                url=row["url"],
                ad_id=row["ad_id"],
                status=row["status"],
            )
            result = CompetitiveWatch(self._olx_db(request)).observe_seller_ads(
                xml,
                own,
                viewed_url=body.get("viewed_url"),
                viewed_ad_id=body.get("viewed_ad_id"),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_competitive_refresh(self, request: Request) -> JSONResponse:
        """Re-link active own listings against the current market."""
        try:
            from aios_core.modules.olx import CompetitiveWatch, OwnAd

            body = (
                await request.json()
                if (request.headers.get("content-length") or "0") != "0"
                else {}
            )
            watch = CompetitiveWatch(self._olx_db(request))
            own_list = [
                OwnAd(
                    title=row["title"],
                    price=row["price"],
                    currency=row["currency"],
                    views=row["last_views"] or 0,
                    url=row["url"],
                    ad_id=row["ad_id"],
                    status=row["status"],
                )
                for row in self._olx_db(request).own_ads(status="active")
            ]
            result = watch.refresh(own_list)
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_profile_edit(self, request: Request) -> JSONResponse:
        """Stage/execute a profile field edit (dry-run default)."""
        try:
            from aios_core.modules.olx import ProfileEditor

            body = await request.json()
            field_key = body.get("field")
            new_value = body.get("value")
            if not field_key or new_value is None:
                return JSONResponse(
                    {"error": "fields 'field' and 'value' are required"},
                    status_code=400,
                )
            editor = ProfileEditor(adb=self.olx_messenger.adb)
            result = editor.apply(
                self._olx_db(request),
                field_key,
                str(new_value),
                confirm=bool(body.get("confirm", False)),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_profile_parse(self, request: Request) -> JSONResponse:
        """Parse a profile/settings screen dump and store the fields."""
        try:
            from aios_core.modules.olx import ProfileParser

            body = await request.json()
            xml_text = body.get("xml")
            if not xml_text:
                return JSONResponse({"error": "field 'xml' is required"}, status_code=400)
            parser = ProfileParser()
            profile = parser.parse_profile(xml_text)
            for key, value in profile.fields.items():
                self._olx_db(request).profile_set(key, value)
            payload = profile.to_dict()
            if body.get("include_settings"):
                texts = parser._texts(xml_text)
                payload["settings"] = parser.settings_from_texts(texts).to_dict()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_profile(self, request: Request) -> JSONResponse:
        """Stored profile fields and pending edits."""
        return JSONResponse({"fields": self._olx_db(request).profile_all()})

    async def _olx_doctor(self, request: Request) -> JSONResponse:
        """Environment readiness checklist for OLX automation."""
        from aios_core.modules.olx import OLXBootstrap

        report = OLXBootstrap().doctor_report()
        return JSONResponse(report)

    async def _olx_autowatch(self, request: Request) -> JSONResponse:
        """Run one full AutoWatch cycle (collect → own → plan → notify)."""
        try:
            from aios_core.modules.olx import AutoWatch, WebhookNotifier

            body = await request.json()
            queries = body.get("queries")
            watch = AutoWatch(
                storage=self._olx_db(request),
                collector=self.olx_collector,
                notifier=WebhookNotifier(url=body.get("webhook_url"), chat_id=body.get("chat_id")),
                max_cards=self._bounded_int(body.get("max_cards"), default=50, maximum=500),
            )
            report = watch.run_cycle(
                queries=queries if isinstance(queries, list) else None,
                collect=bool(body.get("collect", True)),
                min_age_days=float(body.get("min_age_days", 3.0)),
                min_views_per_day=float(body.get("min_views_per_day", 1.0)),
            )
            return JSONResponse(report)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_favorite_alerts(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch

        alerts = FavoritesWatch(self._olx_db(request)).price_alerts()
        return JSONResponse({"count": len(alerts), "alerts": alerts})

    async def _olx_favorite_remove(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch

        fingerprint = request.path_params["fingerprint"]
        removed = FavoritesWatch(self._olx_db(request)).remove(fingerprint)
        return JSONResponse({"fingerprint": fingerprint, "removed": removed})

    async def _olx_favorite_add(self, request: Request) -> JSONResponse:
        try:
            from aios_core.modules.olx import FavoritesWatch

            body = await request.json()
            fingerprint = body.get("fingerprint")
            if not fingerprint:
                return JSONResponse({"error": "field 'fingerprint' is required"}, status_code=400)
            added = FavoritesWatch(self._olx_db(request)).add(fingerprint)
            return JSONResponse({"fingerprint": fingerprint, "added": added})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_favorites(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch

        items = FavoritesWatch(self._olx_db(request)).list()
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_subscription_check(self, request: Request) -> JSONResponse:
        """Match stored ads (optionally only recent) against all subscriptions."""
        try:
            from aios_core.modules.olx import SubscriptionManager

            body = await request.json() if request.method == "POST" else {}
            manager = SubscriptionManager(self._olx_db(request))
            query_filter = body.get("query")
            cards = self._olx_db(request).get_ads(query=query_filter)
            alerts = manager.check_new(cards)
            return JSONResponse({"alerts_count": len(alerts), "alerts": alerts})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_subscription_remove(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import SubscriptionManager

        sub_id = int(request.path_params["subscription_id"])
        removed = SubscriptionManager(self._olx_db(request)).remove(sub_id)
        return JSONResponse({"id": sub_id, "removed": removed})

    async def _olx_subscription_add(self, request: Request) -> JSONResponse:
        try:
            from aios_core.modules.olx import SubscriptionManager

            body = await request.json()
            query = body.get("query")
            if not query:
                return JSONResponse({"error": "field 'query' is required"}, status_code=400)
            sub_id = SubscriptionManager(self._olx_db(request)).add(
                name=body.get("name") or query,
                query=query,
                min_price=body.get("min_price"),
                max_price=body.get("max_price"),
                city=body.get("city"),
            )
            return JSONResponse({"id": sub_id})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_subscriptions(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import SubscriptionManager

        items = SubscriptionManager(self._olx_db(request)).list()
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_own_edit(self, request: Request) -> JSONResponse:
        """Apply an improvement as an edit (dry-run default, `confirm` to run)."""
        try:
            from aios_core.modules.olx import AdImprover, OwnAd, OwnAdEditor

            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [
                row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint
            ]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"],
                price=row["price"],
                currency=row["currency"],
                views=row["last_views"] or 0,
                url=row["url"],
                ad_id=row["ad_id"],
                status=row["status"],
            )
            competitors = self._olx_db(request).get_ads(query=body.get("query"))
            suggestion = AdImprover().improve(own_ad, competitors)
            editor = OwnAdEditor(adb=self.olx_messenger.adb)
            result = editor.apply(own_ad, suggestion, confirm=bool(body.get("confirm", False)))
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_notify(self, request: Request) -> JSONResponse:
        """Send price-drop and stagnant-listing alerts to a webhook."""
        try:
            from aios_core.modules.olx import (
                OwnAdsTracker,
                PriceTracker,
                WebhookNotifier,
                notify_price_drops,
                notify_stagnant,
            )

            body = await request.json()
            notifier = WebhookNotifier(url=body.get("webhook_url"), chat_id=body.get("chat_id"))
            if not notifier.url:
                return JSONResponse({"error": "field 'webhook_url' is required"}, status_code=400)
            tracker = PriceTracker(self._olx_db(request))
            query = body.get("query")
            drops_summary = notify_price_drops(tracker, notifier, query=query)
            stagnant_items = OwnAdsTracker(self._olx_db(request)).stagnant()
            stagnant_summary = notify_stagnant(stagnant_items, notifier)
            return JSONResponse({"drops": drops_summary, "stagnant": stagnant_summary})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_repost(self, request: Request) -> JSONResponse:
        """Repost plan (dry-run default) or guarded execution (`confirm: true`)."""
        try:
            from aios_core.modules.olx import OwnAd, Reposter

            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [
                row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint
            ]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"],
                price=row["price"],
                currency=row["currency"],
                url=row["url"],
                ad_id=row["ad_id"],
                status=row["status"],
            )
            reposter = Reposter(adb=self.olx_messenger.adb)
            result = reposter.repost(own_ad, confirm=bool(body.get("confirm", False)))
            if result.get("status") == "executed":
                self._olx_db(request).own_ad_set_status(fingerprint, "inactive")
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_improve(self, request: Request) -> JSONResponse:
        """Improvement suggestion for one of my listings vs competitors."""
        try:
            from aios_core.modules.olx import AdImprover, OwnAd

            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [
                row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint
            ]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"],
                price=row["price"],
                currency=row["currency"],
                views=row["last_views"] or 0,
                url=row["url"],
                ad_id=row["ad_id"],
                status=row["status"],
            )
            competitors = self._olx_db(request).get_ads(query=body.get("query"))
            suggestion = AdImprover().improve(own_ad, competitors)
            payload = suggestion.to_dict()
            payload["text"] = suggestion.to_text()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_stagnant(self, request: Request) -> JSONResponse:
        """Own listings with too few views per day (repost candidates)."""
        from aios_core.modules.olx import OwnAdsTracker

        min_age = float(request.query_params.get("min_age_days", 3.0))
        min_rate = float(request.query_params.get("min_views_per_day", 1.0))
        items = OwnAdsTracker(self._olx_db(request)).stagnant(
            min_age_days=min_age, min_views_per_day=min_rate
        )
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_own_snapshot(self, request: Request) -> JSONResponse:
        """Record a counters snapshot of own ads (parsed client-side or by the agent)."""
        try:
            from aios_core.modules.olx import OwnAd, OwnAdsTracker

            body = await request.json()
            ads = []
            for raw in body.get("ads") or []:
                ads.append(
                    OwnAd(
                        title=raw.get("title") or "",
                        price=raw.get("price"),
                        currency=raw.get("currency"),
                        views=int(raw.get("views") or 0),
                        favorites=int(raw.get("favorites") or 0),
                        messages=int(raw.get("messages") or 0),
                        status=raw.get("status") or "active",
                        url=raw.get("url"),
                        ad_id=raw.get("ad_id"),
                    )
                )
            result = OwnAdsTracker(self._olx_db(request)).record_snapshot(
                ads, seen_at=body.get("seen_at")
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_list(self, request: Request) -> JSONResponse:
        """List my own tracked listings (filterable by `status`)."""
        items = self._olx_db(request).own_ads(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_outbox_cancel(self, request: Request) -> JSONResponse:
        """Cancel a pending draft by id."""
        try:
            body = await request.json()
            outbox_id = int(body.get("id"))
            cancelled = self._olx_db(request).outbox_mark(outbox_id, "cancelled")
            return JSONResponse({"id": outbox_id, "cancelled": cancelled})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_outbox_send(self, request: Request) -> JSONResponse:
        """Flush every pending draft to the device."""
        try:
            results = self.olx_messenger.flush_outbox()
            return JSONResponse({"processed": len(results), "results": results})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_outbox(self, request: Request) -> JSONResponse:
        """List reply drafts (filterable by `status`)."""
        items = self._olx_db(request).outbox_list(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_chat_reply(self, request: Request) -> JSONResponse:
        """Queue a chat reply (default) or send it (`send_now: true`)."""
        try:
            body = await request.json()
            text = body.get("text") or ""
            if not text.strip():
                return JSONResponse({"error": "field 'text' is required"}, status_code=400)
            result = self.olx_messenger.send_reply(
                chat_key=body.get("chat_key") or "unknown",
                text=text,
                interlocutor=body.get("interlocutor"),
                auto_send=bool(body.get("send_now", False)),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_chats(self, request: Request) -> JSONResponse:
        """List personal chat threads from the device (requires ADB)."""
        try:
            threads = self.olx_messenger.list_chats()
            return JSONResponse(
                {
                    "count": len(threads),
                    "unread_total": sum(t.unread_count for t in threads),
                    "items": [t.to_dict() for t in threads],
                }
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_detail_parse(self, request: Request) -> JSONResponse:
        """Parse a UIAutomator dump of an open ad into structured detail data."""
        try:
            from aios_core.modules.olx import AdDetailParser

            body = await request.json()
            xml_text = body.get("xml")
            if not xml_text:
                return JSONResponse({"error": "field 'xml' is required"}, status_code=400)
            detail = AdDetailParser().parse(xml_text, url=body.get("url"))
            return JSONResponse(detail.to_dict())
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_drops(self, request: Request) -> JSONResponse:
        """Price drops and ads that left the feed (`gone` = sold/removed)."""
        from aios_core.modules.olx import PriceTracker

        query = request.query_params.get("query")
        tracker = PriceTracker(self._olx_db(request))
        drops = tracker.price_drops(query=query)
        gone = tracker.gone_from_feed(query=query)
        return JSONResponse(
            {
                "drops_count": len(drops),
                "drops": [change.to_dict() for change in drops],
                "gone_count": len(gone),
                "gone": [ad.to_dict() for ad in gone],
            }
        )

    async def _olx_history(self, request: Request) -> JSONResponse:
        """Price history for one tracked ad (`fingerprint` is required)."""
        fingerprint = request.query_params.get("fingerprint")
        if not fingerprint:
            return JSONResponse(
                {"error": "query parameter 'fingerprint' is required"},
                status_code=400,
            )
        history = self._olx_db(request).price_history(fingerprint)
        return JSONResponse({"fingerprint": fingerprint, "count": len(history), "history": history})

    def _olx_db(self, request: Request):
        """Profile-scoped OLX storage.

        ``?profile=<name>`` switches the request to that account's isolated
        storage (cached per name); without the parameter the API-wide
        default storage is used. Unknown names raise ``ValueError`` which
        the app-level exception handler maps to HTTP 400.
        """
        name = request.query_params.get("profile")
        if not name:
            return self.olx_storage
        storage = self._olx_profile_storages.get(name)
        if storage is None:
            from aios_core.modules.olx import OLXStorage
            from aios_core.platforms import resolve_profile

            profile = resolve_profile("olx", name, store=self.profile_store)
            storage = OLXStorage(profile.db_path)
            self._olx_profile_storages[name] = storage
        return storage

    # ------------------------------------------------------------------ #
    # Platforms & profiles registry endpoints                             #
    # ------------------------------------------------------------------ #

