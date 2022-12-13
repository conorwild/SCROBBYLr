
def test_index(client):
    response = client.get("/")
    assert b"R<sup>2</sup> - Records for your records!" in response.data