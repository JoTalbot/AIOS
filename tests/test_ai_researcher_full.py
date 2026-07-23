from aios_core.ai_researcher import AIResearcher
def test_researcher():
    r = AIResearcher()
    paper = r.write_paper('AI', [])
    assert paper['status'] == 'draft'
    review = r.peer_review(paper)
    assert review['recommendation'] == 'accept'