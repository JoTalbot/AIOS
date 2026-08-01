"""Knowledge graph view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_knowledge_graph() -> dict:
    return await get("/api/knowledge-graph")


def render() -> None:
    ui.label("Knowledge Graph").classes("text-h6")

    graph_label = ui.label("Loading...").classes("text-body1")
    graph = ui.echart(
        {
            "tooltip": {},
            "series": [
                {
                    "type": "graph",
                    "layout": "force",
                    "roam": True,
                    "label": {"show": True},
                    "force": {"repulsion": 180, "edgeLength": 100},
                    "data": [],
                    "links": [],
                }
            ],
        }
    ).classes("w-full h-96")

    node_table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "label", "label": "Label", "field": "label"},
            {"name": "type", "label": "Type", "field": "type"},
            {"name": "detail", "label": "Detail", "field": "detail"},
        ],
        rows=[],
    ).classes("w-full")

    edge_table = ui.table(
        columns=[
            {"name": "source", "label": "Source", "field": "source"},
            {"name": "target", "label": "Target", "field": "target"},
            {"name": "relation", "label": "Relation", "field": "relation"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_graph() -> None:
        data = await _get_knowledge_graph()
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        graph_label.set_text(f"Nodes: {len(nodes)} | Edges: {len(edges)}")
        graph.options["series"][0]["data"] = [
            {"id": str(node.get("id", "")), "name": str(node.get("label", node.get("id", ""))), "value": node.get("type", "")}
            for node in nodes
        ]
        graph.options["series"][0]["links"] = [
            {"source": str(edge.get("source", "")), "target": str(edge.get("target", "")), "label": {"show": True, "formatter": str(edge.get("relation", ""))}}
            for edge in edges
        ]
        graph.update()
        node_table.rows = nodes
        edge_table.rows = edges

    ui.button("Refresh graph", on_click=load_graph).props("flat")
