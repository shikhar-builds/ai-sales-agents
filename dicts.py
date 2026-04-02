import json

clients = [
    {"name": "Square",    "revenue": 89000000, "risk": "Low"},
    {"name": "FIS",       "revenue": 71000000, "risk": "Medium"},
    {"name": "Adyen",     "revenue": 64000000, "risk": "Low"},
    {"name": "Worldline", "revenue": 45000000, "risk": "High"},
]

# Print all clients
for client in clients:
    print(f"{client['name']} — £{client['revenue']:,} — Risk: {client['risk']}")

# Save to JSON
with open("clients.json", "w") as f:
    json.dump(clients, f, indent=4)

print("\nSaved to clients.json!")