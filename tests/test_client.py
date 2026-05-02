from ntes import NTESClient

def test_search_structure():
    client = NTESClient()
    res = client.search("double")

    assert isinstance(res, dict)
    assert "Trains" in res