#!/usr/bin/env python3
"""Haalt alle plekken met glutenvrije opties in Nederland op uit OpenStreetMap (Overpass)
en schrijft ze naar places-nl.json, in hetzelfde formaat als het `Place`-model van de Glutenmaps-app.

Draait dagelijks via .github/workflows/update-places.yml. Alleen standaardbibliotheek nodig.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]
ROUNDS = 6
OUTPUT = Path(__file__).with_name("places-nl.json")
# Veiligheidsgrens: een kleiner resultaat is vrijwel zeker een mislukte of onvolledige query.
MIN_EXPECTED_PLACES = 500

QUERY = """
[out:json][timeout:300];
area["ISO3166-1"="NL"][admin_level=2]->.nl;
(
  nwr(area.nl)["diet:gluten_free"~"^(yes|only)$"]["name"]["amenity"~"^(restaurant|cafe|fast_food|bar|pub|ice_cream)$"];
  nwr(area.nl)["diet:gluten_free"~"^(yes|only)$"]["name"]["shop"="bakery"];
);
out center tags;
"""


def fetch():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    for attempt in range(1, ROUNDS + 1):
        for url in ENDPOINTS:
            try:
                request = urllib.request.Request(
                    url, data=body, headers={"User-Agent": "Glutenmaps-feed/1.0 (antonwubben.nl)"}
                )
                with urllib.request.urlopen(request, timeout=330) as response:
                    data = json.load(response)
                # Een overbelaste server geeft soms 200 met een `remark` en lege elementen.
                if data.get("remark") or not data.get("elements"):
                    print(f"{url}: onbruikbaar antwoord ({data.get('remark')})", file=sys.stderr)
                    continue
                return data["elements"]
            except Exception as error:  # noqa: BLE001 - elke fout betekent: volgende server proberen
                print(f"{url}: {error}", file=sys.stderr)
        print(f"Ronde {attempt} mislukt, wacht even…", file=sys.stderr)
        time.sleep(30 * attempt)
    raise SystemExit("Geen enkele Overpass-server gaf een bruikbaar antwoord.")


CATEGORIES = {
    "restaurant": "restaurant",
    "cafe": "cafe",
    "fast_food": "fastFood",
    "bar": "bar",
    "pub": "bar",
    "ice_cream": "iceCream",
}


def category(tags):
    if tags.get("amenity") in CATEGORIES:
        return CATEGORIES[tags["amenity"]]
    if tags.get("shop") == "bakery":
        return "bakery"
    return None


def address(tags):
    street = " ".join(v for v in (tags.get("addr:street"), tags.get("addr:housenumber")) if v)
    city = " ".join(v for v in (tags.get("addr:postcode"), tags.get("addr:city")) if v)
    lines = [line for line in (street, city) if line]
    return "\n".join(lines) or None


def place(element):
    tags = element.get("tags") or {}
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    kind = category(tags)
    if not tags.get("name") or lat is None or lon is None or kind is None:
        return None
    result = {
        "id": f"{element['type']}/{element['id']}",
        "name": tags["name"],
        "latitude": lat,
        "longitude": lon,
        "category": kind,
        "glutenLevel": "only" if tags.get("diet:gluten_free") == "only" else "options",
    }
    # Optionele velden laten we weg als ze leeg zijn; Swift decodeert die als nil.
    for key, value in (
        ("glutenSource", tags.get("source:diet:gluten_free")),
        ("glutenCheckDate", tags.get("check_date:diet:gluten_free")),
        ("address", address(tags)),
        ("website", tags.get("website") or tags.get("contact:website")),
        ("phone", tags.get("phone") or tags.get("contact:phone")),
    ):
        if value:
            result[key] = value
    return result


def main():
    places = sorted(filter(None, map(place, fetch())), key=lambda p: p["id"])
    if len(places) < MIN_EXPECTED_PLACES:
        raise SystemExit(f"Slechts {len(places)} plekken; bestand wordt niet overschreven.")
    OUTPUT.write_text(json.dumps(places, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(places)} plekken geschreven naar {OUTPUT.name}")


if __name__ == "__main__":
    main()
