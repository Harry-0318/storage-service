from fastapi.testclient import TestClient
from main import app
from auth import ADMIN_TOKEN

client = TestClient(app)

def test_flow():
    tool_name = "test_survey_bot"
    tool_token = "survey-secure-token"
    schema = [
        {"name": "user_id", "type": "int"},
        {"name": "feedback", "type": "str"}
    ]

    print("1. Registering Tool...")
    response = client.post(
        "/register-tool",
        json={
            "tool_name": tool_name,
            "token": tool_token,
            "schema": schema
        },
        headers={"admin-token": ADMIN_TOKEN}
    )
    print(response.json())
    assert response.status_code == 200

    print("\n2. Storing Data...")
    payload = {"user_id": 101, "feedback": "Great service!"}
    response = client.post(
        f"/tools/{tool_name}",
        json=payload,
        headers={"token": tool_token}
    )
    print(response.json())
    assert response.status_code == 200

    print("\n3. Retrieving Data...")
    response = client.get(f"/tools/{tool_name}")
    data = response.json()
    print(data)
    assert response.status_code == 200
    assert len(data) >= 1
    assert data[0]["user_id"] == 101

    print("\n4. Testing Invalid Payload (Type Mismatch)...")
    bad_payload = {"user_id": "not-an-int", "feedback": "oops"}
    response = client.post(
        f"/tools/{tool_name}",
        json=bad_payload,
        headers={"token": tool_token}
    )
    print(f"Status: {response.status_code}, Response: {response.json()}")
    assert response.status_code == 400

    print("\n5. Deleting Tool...")
    response = client.delete(
        f"/tools/{tool_name}",
        headers={"admin-token": ADMIN_TOKEN}
    )
    print(response.json())
    assert response.status_code == 200

    print("\n6. Verifying Deletion...")
    response = client.get(f"/tools/{tool_name}")
    assert response.status_code == 404
    print("Tool successfully deleted and not found.")

if __name__ == "__main__":
    try:
        test_flow()
        print("\n✅ Verification Successful!")
    except AssertionError as e:
        print("\n❌ Verification Failed!")
        raise e
    except Exception as e:
        print(f"\n❌ Javascript Error: {e}")
        raise e
