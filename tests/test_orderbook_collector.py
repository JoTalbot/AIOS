from scripts.collect_orderbook_snapshots import OrderbookStore, collect_once, normalize


def test_normalize_and_store(tmp_path):
    book = {"timestamp": 1000, "bids": [[100, 2], [99, 1]], "asks": [[101, 3], [102, 1]]}
    row = normalize("x", "BTC", book, 12.0, 2)
    assert row["spread_bps"] > 0 and row["bid_depth_usd"] == 299 and row["ask_depth_usd"] == 405
    store = OrderbookStore(tmp_path / "o.db")

    class Client:
        def fetch_order_book(self, pair, limit):
            return book

    assert collect_once({"x": Client()}, ["BTC"], store) == {"saved": 1, "errors": 0}
    assert store.db.execute("select count(*) from snapshots").fetchone()[0] == 1
    store.close()
