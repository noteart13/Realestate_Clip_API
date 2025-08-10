import re
from typing import List, Dict
from duckduckgo_search import DDGS
from app import config

RE_URL_REA = re.compile(r"https?://(www\.)?realestate\.com\.au/[^\s]+", re.I)
RE_URL_DOM = re.compile(r"https?://(www\.)?domain\.com\.au/[^\s]+", re.I)


def search_address(address: str, max_results: int | None = None) -> Dict[str, List[str]]:
    max_results = max_results or config.MAX_RESULTS
    q_rea = f'"{address}" site:realestate.com.au'
    q_dom = f'"{address}" site:domain.com.au'

    urls_rea: List[str] = []
    urls_dom: List[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(q_rea, region=config.DDG_REGION, max_results=max_results*2):
            href = (r.get("href") or r.get("link") or "").strip()
            if href and RE_URL_REA.match(href):
                urls_rea.append(href)
                if len(urls_rea) >= max_results:
                    break
        for r in ddgs.text(q_dom, region=config.DDG_REGION, max_results=max_results*2):
            href = (r.get("href") or r.get("link") or "").strip()
            if href and RE_URL_DOM.match(href):
                urls_dom.append(href)
                if len(urls_dom) >= max_results:
                    break
    return {"realestate": urls_rea, "domain": urls_dom}