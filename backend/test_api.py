import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_logs():
    client = TestClient(app)
    # Login to get token
    r1 = client.post("/api/v1/auth/login/access-token", data={"username":"admin@example.com","password":"admin_password"})
    token = r1.json()["access_token"]
    
    # Hit /audit/logs
    r2 = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token}"})
    print(r2.status_code, r2.json())

test_logs()
