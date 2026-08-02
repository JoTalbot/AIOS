class OLXAppActions:
    """OLX application actions foundation."""

    def search(self, query):
        return {
            "action": "search",
            "query": query,
        }

    def monitor_listing(self, listing_id):
        return {
            "action": "monitor",
            "listing_id": listing_id,
        }
