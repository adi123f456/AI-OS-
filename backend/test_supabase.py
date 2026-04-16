"""
Quick test to verify Supabase integration is working.
Tests: Register → Login → Chat → Memory → Usage
"""

import httpx
import json
import sys

BASE = "http://localhost:8000"

def test():
    client = httpx.Client(base_url=BASE, timeout=30)
    
    print("=" * 50)
    print("  AI OS — Supabase Integration Test")
    print("=" * 50)
    
    # 1. Health Check
    print("\n[1] Health Check...")
    r = client.get("/health")
    health = r.json()
    print(f"    Status: {health['status']}")
    print(f"    Database: {health['components']['database']}")
    print(f"    Redis: {health['components']['redis']}")
    print(f"    Groq: {health['components']['groq']}")
    
    if health["components"]["database"] != "connected":
        print("\n[FAIL] Supabase NOT connected! Aborting.")
        sys.exit(1)
    print("    ✅ PASS")
    
    # 2. Register
    print("\n[2] Register User...")
    r = client.post("/api/auth/register", json={
        "email": "supatest@aios.dev",
        "password": "SecurePass123!"
    })
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token", "")
        print(f"    User ID: {data.get('user', {}).get('id', 'N/A')}")
        print(f"    Token: {token[:30]}...")
        print("    ✅ PASS")
    elif r.status_code == 409:
        # User might already exist, try login
        print(f"    User already exists, trying login...")
        r = client.post("/api/auth/login", json={
            "email": "supatest@aios.dev",
            "password": "SecurePass123!"
        })
        data = r.json()
        token = data.get("access_token", "")
        print(f"    Token: {token[:30]}...")
        print("    ✅ PASS (via login)")
    else:
        print(f"    Response: {r.text}")
        print("    ❌ FAIL")
        token = None

    if not token:
        print("\n[FAIL] No auth token! Aborting.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Chat (AI response via Groq)
    print("\n[3] Chat Endpoint...")
    r = client.post("/api/chat", json={
        "message": "What is 2+2? Reply in one word."
    }, headers=headers)
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        chat = r.json()
        print(f"    Model: {chat.get('model_used', 'N/A')}")
        print(f"    Response: {chat.get('response', '')[:80]}...")
        print(f"    Cost: ${chat.get('cost', 0)}")
        print("    ✅ PASS")
    else:
        print(f"    Response: {r.text[:200]}")
        print("    ❌ FAIL")

    # 4. Memory
    print("\n[4] Memory Storage...")
    r = client.post("/api/memory", json={
        "key": "test_preference",
        "value": "dark_mode",
        "category": "ui"
    }, headers=headers)
    print(f"    Store Status: {r.status_code}")
    
    r = client.get("/api/memory", headers=headers)
    if r.status_code == 200:
        memories = r.json()
        print(f"    Memories Found: {len(memories.get('memories', []))}")
        print("    ✅ PASS")
    else:
        print(f"    Response: {r.text[:200]}")
        print("    ❌ FAIL")

    # 5. Usage Stats
    print("\n[5] Usage Stats...")
    r = client.get("/api/usage", headers=headers)
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        usage = r.json()
        print(f"    Requests Today: {usage.get('requests_today', 0)}")
        print(f"    Total Cost: ${usage.get('total_cost', 0)}")
        print("    ✅ PASS")
    else:
        print(f"    Response: {r.text[:200]}")
        print("    ❌ FAIL")

    # 6. Models List
    print("\n[6] Models List...")
    r = client.get("/api/models", headers=headers)
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        models = r.json()
        print(f"    Available: {len(models.get('models', []))} models")
        print("    ✅ PASS")
    else:
        print(f"    Response: {r.text[:200]}")
        print("    ❌ FAIL")

    print("\n" + "=" * 50)
    print("  🎉 ALL TESTS COMPLETE — SUPABASE CONNECTED!")
    print("=" * 50)

if __name__ == "__main__":
    test()
