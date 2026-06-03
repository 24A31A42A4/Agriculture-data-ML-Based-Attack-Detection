import asyncio
import httpx
from colorama import init, Fore

init(autoreset=True)

async def test_simulations():
    print(Fore.CYAN + "\nTesting Attack Simulation & Reset Trust Endpoints...")
    
    # 1. Login to get token
    async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
        try:
            login_data = {"username": "admin@example.com", "password": "admin_password"}
            r = await client.post("/auth/login", data=login_data)
            if r.status_code != 200:
                print(Fore.RED + f"Login failed: {r.status_code}")
                return
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # 2. Get device
            r = await client.get("/devices", headers=headers)
            devices = r.json()
            if not devices:
                print(Fore.RED + "No devices found.")
                return
            device_id = devices[0]["device_id"]
            print(Fore.GREEN + f"Found device: {device_id}")
            
            # 3. Test Reset Trust
            print(Fore.CYAN + "Testing Reset Trust...")
            r = await client.post(f"/devices/{device_id}/reset-trust", headers=headers)
            if r.status_code == 200:
                print(Fore.GREEN + f"Reset Trust Success! New score: {r.json()['trust_score']}")
            else:
                print(Fore.RED + f"Reset Trust Failed: {r.text}")
                
            # 4. Test Simulation
            print(Fore.CYAN + "Testing ML Anomaly Simulation...")
            r = await client.post(f"/attack-sim/ml-anomaly/{device_id}", headers=headers, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                print(Fore.GREEN + "ML Anomaly Success!")
                if "attack_trace" in data and len(data["attack_trace"]) > 0:
                    print(Fore.GREEN + f"Attack trace found with {len(data['attack_trace'])} steps.")
                    for step in data["attack_trace"]:
                        print(f"  - [{step['status'].upper()}] {step['step_name']}: {step['description']}")
                else:
                    print(Fore.RED + "No attack_trace found in response!")
            else:
                print(Fore.RED + f"ML Anomaly Failed: {r.text}")
                
        except Exception as e:
            print(Fore.RED + f"Error during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test_simulations())
