from typing import Dict, Any

class AIOS:
    def __init__(self):
        self.runtime = None
        self.tools = ToolRegistry()
        self.guard = Guard()  # Assuming Guard is a class for authorization and permissions
        self.stats = lambda: {"stats": "AIOS runtime statistics"}  # Placeholder for stats retrieval

    def register_tool(self, tool_def: ToolDefinition):
        self.tools.register(tool_def)

    def handle_memory_store(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation of the memory store tool
        pass

    def handle_memory_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation of the memory search tool
        pass

    def handle_knowledge_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation of the knowledge graph query tool
        pass

    def _register_olx_tools(self):
        """Register read-only OLX Parser Agent tools (market intelligence)."""

        self.tools.register(
            ToolDefinition(
                name="olx_market_stats",
                description="Competitor market statistics for an OLX search query: price min/max/mean/median, TOP share, top cities.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query filter (optional — whole store)",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name — storage is resolved from the profiles registry",
                        },
                    },
                },
                handler=lambda p: self._olx_market_stats(p),
                category="olx",
                risk_level="low",
            )
        )

        self.tools.register(
            ToolDefinition(
                name="olx_listing_recommend",
                description="Listing advice for a draft OLX ad: suggested price, market verdict, title keywords, TOP promotion decision.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query of competitors",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Draft listing title",
                        },
                        "price": {
                            "type": "number",
                            "description": "Draft listing price",
                        },
                    },
                },
                handler=lambda p: self._olx_listing_recommend(p),
                category="olx",
                risk_level="low",
            )
        )

        self.tools.register(
            ToolDefinition(
                name="olx_price_drops",
                description="OLX ads with a detected price drop plus listings that left the feed (sold/removed).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query filter (optional)",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name",
                        },
                    },
                },
                handler=lambda p: self._olx_price_drops(p),
                category="olx",
                risk_level="low",
            )
        )

    def _olx_market_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from aios_core.modules.olx import CompetitorAnalyzer

        store = self._olx_store(params.get("profile"))
        query = params.get("query")
        ads = store.get_ads(query=query)
        return CompetitorAnalyzer().analyze(ads, query=query).to_dict()

    def _olx_listing_recommend(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from dataclasses import asdict

        from aios_core.modules.olx import AdCard, RecommendationEngine

        store = self._olx_store(params.get("profile"))
        query = params.get("query")
        ads = store.get_ads(query=query)
        my_ad = None
        if params.get("title") is not None or params.get("price") is not None:
            my_ad = AdCard(
                title=params.get("title") or "",
                price=params.get("price"),
                currency="UAH",
                query=query,
            )
        advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
        payload = asdict(advice)
        payload["text"] = advice.to_text()
        return payload

    def _olx_price_drops(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from aios_core.modules.olx import PriceTracker

        store = self._olx_store(params.get("profile"))
        tracker = PriceTracker(store)
        query = params.get("query")
        return {
            "drops": [change.to_dict() for change in tracker.price_drops(query=query)],
            "gone": [ad.to_dict() for ad in tracker.gone_from_feed(query=query)],
        }

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_memory_store(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for memory store tool."""
        from aios_core.memory_manager import MemoryManager

        if params.get("category") == "personal":
            raise PermissionError("Personal memory is available only through the authenticated REST API")

        mm = MemoryManager(db=self.runtime.db)
        tags = params.get("tags", "")
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # MemoryManager.store() expects content as a dict
        return mm.store(
            content={"text": params["content"]},
            category=params["category"],
            tags=tag_list,
        )

    def _handle_memory_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for memory search tool."""
        from aios_core.memory_manager import MemoryManager

        if params.get("category") == "personal":
            raise PermissionError("Personal memory is available only through the authenticated REST API")

        mm = MemoryManager(db=self.runtime.db)
        results = mm.search(
            query=params.get("query", ""),
            category=params.get("category"),
            limit=params.get("limit", 20),
        )
        return {"results": results, "count": len(results)}

    def handle_knowledge_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for knowledge graph query tool."""
        from aios_core.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(db=self.runtime.db)
        results = kg.find_nodes(
            label=params.get("query", ""),
            node_type=params.get("node_type"),
            limit=params.get("limit", 20),
        )
        return