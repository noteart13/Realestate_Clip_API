import re
from typing import Optional
from app.schemas import PropertyItem
from app.scrapers.common import extract_from_jsonld

LISTING_ID_RE = re.compile(r"/property-[^/]+-([a-z0-9]+)", re.I)


def parse_listing_id(url: str) -> Optional[str]:
    m = LISTING_ID_RE.search(url)
    return m.group(1) if m else None


def transform(url: str, html: str) -> PropertyItem:
    data = extract_from_jsonld(html)
    item = PropertyItem(
        source="domain",
        url=url,
        listing_id=parse_listing_id(url),
        title=data.get("title"),
        address=data.get("address"),
        price=(data.get("raw") or {}).get("offers", {}).get("price") if (data.get("raw") or {}).get("offers") else data.get("price"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        parking=data.get("parking"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        description=data.get("description"),
        images=data.get("images", []),
        features={},
        raw=data.get("raw") or {},
    )
    return item