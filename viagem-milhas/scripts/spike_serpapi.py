"""SPIKE descartavel: UMA busca real do trajeto aberto, para saber o formato da resposta.

Grava a resposta crua em tests/fixtures/serpapi_open_jaw.json (sem a chave) e imprime so um resumo.
Uso: python scripts/spike_serpapi.py
"""
import json
import os
import sys

import requests

key = os.environ.get("SERPAPI_KEY")
if not key:
    sys.exit("SERPAPI_KEY nao definida")

params = {
    "engine": "google_flights",
    "type": "3",  # multi-city
    "multi_city_json": json.dumps(
        [
            {"departure_id": "GIG", "arrival_id": "BUD", "date": "2027-07-10"},
            {"departure_id": "BER", "arrival_id": "GIG", "date": "2027-07-22"},
        ]
    ),
    "adults": "2",
    "currency": "BRL",
    "hl": "pt",
    "gl": "br",
    "travel_class": "1",
    "api_key": key,
}
resp = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
text = resp.text.replace(key, "***")
print("HTTP", resp.status_code, "| bytes", len(text))

data = json.loads(text)
print("chaves de topo:", sorted(data.keys()))
if "error" in data:
    print("ERRO da API:", data["error"])
for group in ("best_flights", "other_flights"):
    items = data.get(group, [])
    print(group, "->", len(items), "ofertas")
    if items:
        first = items[0]
        print("  primeira oferta, chaves:", sorted(first.keys()))
        print("  preco:", first.get("price"), "| tem departure_token:", "departure_token" in first)
        if first.get("flights"):
            print("  trechos de voo:", len(first["flights"]), "| chaves do 1o:", sorted(first["flights"][0].keys()))
        print("  layovers:", first.get("layovers"))

os.makedirs("tests/fixtures", exist_ok=True)
with open("tests/fixtures/serpapi_open_jaw.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("fixture salva")
