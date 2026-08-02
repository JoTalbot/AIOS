class ListingMonitor:
    """OLX listing monitoring foundation."""

    def __init__(self):
        self.listings = []

    def track(self, listing):
        self.listings.append(listing)
        return listing

    def all(self):
        return self.listings
