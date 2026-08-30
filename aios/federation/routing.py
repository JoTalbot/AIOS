class FederationRouter:
    def route_task(self, task, nodes):
        capable = [n for n in nodes if not task.get("capability") or task["capability"] in n.capabilities]
        return capable[0] if capable else None
