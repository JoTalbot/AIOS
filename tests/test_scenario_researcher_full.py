"""Researcher full scenario."""
from aios_core.ai_researcher import AIResearcher
def test_researcher_full():
    r = AIResearcher()
    topics = ["AI", "ML", "DL", "RL", "NLP"]
    papers = []
    for t in topics:
        p = r.write_paper(t, [{"exp": f"test_{t}"}])
        papers.append(p)
    assert len(papers) == 5
    assert r.stats()["papers"] == 5
    for p in papers:
        review = r.peer_review(p)
        assert review["recommendation"] == "accept"
