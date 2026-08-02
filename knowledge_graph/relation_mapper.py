class RelationMapper:
    """AIOS relation mapping foundation."""

    def map(self, source, target):
        return {
            "source": source,
            "target": target,
            "relation": True
        }
