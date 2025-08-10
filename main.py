from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import PropertyItem, SearchResponse, EmbedRequest
from app.utils.http import Http
from app.scrapers import realestate_au, domain_au
from app.scrapers.common import extract_from_jsonld
from app import config
from app.search import search_address
from fastapi import Request
from fastapi.responses import JSONResponse
from duckduckgo_search.exceptions import RatelimitException
import asyncio


app = FastAPI(title="Real Estate Aggregator + CLIP", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/search", response_model=SearchResponse)
async def search(address: str = Query(..., description="Full street address")):
    return search_address(address)

@app.get("/scrape", response_model=PropertyItem)
async def scrape(url: str = Query(...)):
    http = Http()
    try:
        html = await http.get_text(url)
    finally:
        await http.close()

    if "realestate.com.au" in url:
        return realestate_au.transform(url, html)
    if "domain.com.au" in url:
        return domain_au.transform(url, html)
    raise HTTPException(status_code=400, detail="Unsupported domain")

@app.get("/listings", response_model=List[PropertyItem])
async def listings(address: str = Query(...)):
    urls = search_address(address)
    tasks = []
    http = Http()
    async def _fetch(url: str):
        try:
            html = await http.get_text(url)
            if "realestate.com.au" in url:
                return realestate_au.transform(url, html)
            elif "domain.com.au" in url:
                return domain_au.transform(url, html)
        except Exception:
            return None
    for u in urls.get("realestate", []) + urls.get("domain", []):
        tasks.append(asyncio.create_task(_fetch(u)))
    out = [x for x in await asyncio.gather(*tasks) if x is not None]
    await http.close()
    return out

from app.clip_embed import embed_image_urls  # noqa: E402

@app.post("/embed")
async def embed(req: EmbedRequest):
    vecs = await embed_image_urls(req.image_urls)
    return {"vectors": vecs, "dim": (len(vecs[0]) if vecs and vecs[0] else 0)}


@app.exception_handler(RatelimitException)
async def ratelimit_handler(request: Request, exc: RatelimitException):
    return JSONResponse(
        status_code=429,
        content={"detail": "Search provider rate-limited. Please retry later."},
    )