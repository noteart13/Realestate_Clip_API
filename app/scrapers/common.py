import json
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

JSONLD_TYPE_CANDIDATES = {"RealEstateListing", "Residence", "Apartment", "House", "SingleFamilyResidence"}


def _parse_jsonld_blocks(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for s in soup.find_all("script"):
        t = (s.get("type") or "").lower()
        if "ld+json" in t:
            raw = s.string or s.text
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                # Attempt to repair common trailing comma issues
                fixed = re.sub(r",\s*([}\]])", r"\1", raw)
                try:
                    data = json.loads(fixed)
                except Exception:
                    continue
            if isinstance(data, list):
                out.extend([x for x in data if isinstance(x, dict)])
            elif isinstance(data, dict):
                out.append(data)
    return out


def extract_from_jsonld(html: str) -> Dict[str, Any]:
    blocks = _parse_jsonld_blocks(html)
    best = None
    for b in blocks:
        types = {b.get("@type")} | set(b.get("@type", []) if isinstance(b.get("@type"), list) else [])
        if types & JSONLD_TYPE_CANDIDATES:
            best = b
            break
    if not best and blocks:
        best = blocks[0]

    result: Dict[str, Any] = {"raw": best or {}}
    if not best:
        return result

    # Address
    addr = best.get("address") or {}
    if isinstance(addr, dict):
        parts = [addr.get("streetAddress"), addr.get("addressLocality"), addr.get("addressRegion"), addr.get("postalCode"), addr.get("addressCountry")]
        result["address"] = ", ".join([p for p in parts if p]) or None

    # Geo
    geo = best.get("geo") or {}
    if isinstance(geo, dict):
        try:
            result["latitude"] = float(geo.get("latitude")) if geo.get("latitude") is not None else None
            result["longitude"] = float(geo.get("longitude")) if geo.get("longitude") is not None else None
        except Exception:
            pass

    # Name / description
    result["title"] = best.get("name") or best.get("headline")
    result["description"] = best.get("description")

    # Price/bed/bath/car often lives inside offers or additionalProperty
    offers = best.get("offers") or {}
    if isinstance(offers, dict):
        result["price"] = offers.get("price") or offers.get("priceCurrency")
        if not result["price"]:
            result["price"] = offers.get("name")

    # Quantities from any numeric fields present
    def _num(b):
        try:
            return float(b)
        except Exception:
            return None

    # Common custom properties
    for k in ["numberOfBedrooms", "bedrooms", "bed"]:
        if k in best:
            result["bedrooms"] = _num(best[k])
            break
    for k in ["numberOfBathroomsTotal", "numberOfBathrooms", "bathrooms", "bath"]:
        if k in best:
            result["bathrooms"] = _num(best[k])
            break
    for k in ["numberOfParkingSpaces", "parking", "carSpaces", "carports"]:
        if k in best:
            result["parking"] = _num(best[k])
            break

    # Images
    imgs: List[str] = []
    for key in ("image", "images"):
        if key in best:
            v = best[key]
            if isinstance(v, list):
                imgs.extend([str(x) for x in v if isinstance(x, (str,))])
            elif isinstance(v, str):
                imgs.append(v)
    result["images"] = list(dict.fromkeys(imgs))[:20]

    return result