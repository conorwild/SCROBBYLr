from flask import session

def test_signup(client):
    response = client.post("/signup", 
        data={
            "name": None,
            "email": "test@test.com",
            "password": "asdfasdf",
        }
    )
    assert response.status_code == 422
    assert b"Name: Missing data for required field" in response.data