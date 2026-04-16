"""Quick test script for AI OS chat endpoint."""
import httpx

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzNDc1MzJmYS1lMjQ3LTQxNGMtOWRjNC0yOTU2MzMzOWM1OWUiLCJlbWFpbCI6InRlc3RAYWlvcy5jb20iLCJ0aWVyIjoiZnJlZSIsImlhdCI6MTc3NjAyMzA2OCwiZXhwIjoxNzc2MTA5NDY4fQ.v5OChZhWaKVNEVL8QlK7IaslxCxxVHouyByUDsVZuTc"

# Test 1: Chat endpoint
print("=" * 50)
print("TEST 1: Chat Endpoint")
print("=" * 50)
r = httpx.post(
    "http://localhost:8000/api/chat",
    json={"messages": [{"role": "user", "content": "What is AI OS? Explain in 2 sentences."}]},
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=30,
)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Model Used: {data.get('model_used')}")
    print(f"Routing: {data.get('routing_reason')}")
    print(f"Cost: ${data.get('cost', 0):.6f}")
    print(f"Tokens: {data.get('tokens_input', 0)} in / {data.get('tokens_output', 0)} out")
    print(f"Response: {data.get('content', '')[:500]}")
else:
    print(f"Error: {r.text}")

# Test 2: Usage endpoint
print("\n" + "=" * 50)
print("TEST 2: Usage Endpoint")
print("=" * 50)
r2 = httpx.get(
    "http://localhost:8000/api/usage",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10,
)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    data2 = r2.json()
    print(f"Tier: {data2.get('tier')}")
    print(f"Requests Today: {data2.get('requests_today')}/{data2.get('daily_limit')}")
    print(f"Cost Today: ${data2.get('cost_today', 0):.6f}")

# Test 3: Memory endpoint
print("\n" + "=" * 50)
print("TEST 3: Memory Endpoint")
print("=" * 50)
r3 = httpx.post(
    "http://localhost:8000/api/memory",
    json={"key": "preferred_language", "value": "Python", "category": "preference", "importance": 0.9},
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10,
)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    print(f"Memory stored: {r3.json()}")

# Test 4: Waitlist endpoint
print("\n" + "=" * 50)
print("TEST 4: Waitlist Endpoint")
print("=" * 50)
r4 = httpx.post(
    "http://localhost:8000/api/waitlist",
    json={"email": "demo@aios.com"},
    timeout=10,
)
print(f"Status: {r4.status_code}")
if r4.status_code == 200:
    print(f"Result: {r4.json()}")

# Test 5: Models list
print("\n" + "=" * 50)
print("TEST 5: Available Models")
print("=" * 50)
r5 = httpx.get(
    "http://localhost:8000/api/models",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10,
)
print(f"Status: {r5.status_code}")
if r5.status_code == 200:
    data5 = r5.json()
    print(f"Tier: {data5.get('tier')}")
    for m in data5.get("models", []):
        print(f"  - {m['name']} ({m['provider']}) | Strengths: {', '.join(m['strengths'])}")

print("\n" + "=" * 50)
print("ALL TESTS COMPLETE")
print("=" * 50)
