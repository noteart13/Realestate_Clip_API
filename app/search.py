import re, time, random
from typing import List, Dict
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
from app import config

RE_URL_REA = re.compile(r"https?://(www\.)?realestate\.com\.au/[^\s]+", re.I)
RE_URL_DOM = re.compile(r"https?://(www\.)?domain\.com\.au/[^\s]+", re.I)

def _ddg_text(query: str, max_results: int) -> List[str]:
    attempt = 0
    while True:
        try:
            out: List[str] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=config.DDG_REGION, max_results=max_results*2):
                    href = (r.get("href") or r.get("link") or "").strip()
                    if href:
                        out.append(href)
                        if len(out) >= max_results:
                            break
            return out
        except RatelimitException:
            if attempt >= config.SEARCH_RETRIES:
                raise
            wait = (config.SEARCH_BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
            time.sleep(wait)
            attempt += 1

def search_address(address: str, max_results: int | None = None) -> Dict[str, List[str]]:
    max_results = max_results or config.MAX_RESULTS
    q_rea = f'"{address}" site:realestate.com.au'
    q_dom = f'"{address}" site:domain.com.au'

    urls_rea, urls_dom = [], []
    for href in _ddg_text(q_rea, max_results):
        if RE_URL_REA.match(href):
            urls_rea.append(href)
            if len(urls_rea) >= max_results: break
    for href in _ddg_text(q_dom, max_results):
        if RE_URL_DOM.match(href):
            urls_dom.append(href)
            if len(urls_dom) >= max_results: break
    return {"realestate": urls_rea, "domain": urls_dom}
