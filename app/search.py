import re, time, random
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
from app import config

RE_URL_REA = re.compile(r"https?://(www\.)?realestate\.com\.au/[^\s]+", re.I)
RE_URL_DOM = re.compile(r"https?://(www\.)?domain\.com\.au/[^\s]+", re.I)

SEARCH_RETRIES = getattr(config, "SEARCH_RETRIES", 4)
BACKOFF_BASE   = getattr(config, "SEARCH_BACKOFF_BASE", 1.8)

def _normalize_ddg_href(href: str) -> str:
    """Giải mã link /l/?uddg=... -> URL đích thật"""
    if not href:
        return ""
    if href.startswith("/"):
        href = urljoin("https://duckduckgo.com", href)
    try:
        u = urlparse(href)
        if u.netloc.endswith("duckduckgo.com") and u.path.startswith("/l/"):
            qs = parse_qs(u.query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
    except Exception:
        pass
    return href

def _ddg_html_fallback(query: str, max_results: int) -> List[str]:
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": config.USER_AGENT}) as c:
            r = c.get("https://duckduckgo.com/html/", params={"q": query})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            out: List[str] = []
            for a in soup.select("a.result__a, a.result__url, a[href].result__a"):
                href = _normalize_ddg_href(a.get("href", "").strip())
                if href:
                    out.append(href)
                    if len(out) >= max_results:
                        break
            return out
    except Exception:
        return []

def _ddg_text(query: str, max_results: int) -> List[str]:
    attempt = 0
    while True:
        try:
            urls: List[str] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=config.DDG_REGION, max_results=max_results*2):
                    href = (r.get("href") or r.get("link") or "").strip()
                    if href:
                        urls.append(href)
                        if len(urls) >= max_results:
                            break
            return urls
        except RatelimitException:
            if attempt >= SEARCH_RETRIES:
                return _ddg_html_fallback(query, max_results)
            time.sleep((BACKOFF_BASE ** attempt) + random.uniform(0, 0.5))
            attempt += 1
        except Exception:
            return _ddg_html_fallback(query, max_results)

def _variants(address: str) -> List[str]:
    """Sinh biến thể query để nới điều kiện khớp."""
    a = address.strip()
    outs = {a}
    # Bỏ số căn/unit prefix: "107/131 ..." -> "131 ..."
    outs.add(re.sub(r"^\s*\d+\s*/\s*", "", a))
    # Bỏ postcode (4 chữ số cuối)
    outs.add(re.sub(r"\b\d{4}\b", "", a).strip())
    # Bỏ số nhà đầu
    outs.add(re.sub(r"^\s*\d+[^A-Za-z]+", "", a).strip())
    # Đổi QLD <-> Qld
    outs.add(a.replace(" QLD ", " Qld "))
    outs.add(a.replace(" Qld ", " QLD "))
    # Biến thể không có ngoặc kép (DDG khớp rộng hơn)
    return [s for s in outs if s]

def _dedupe(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def search_address(address: str, max_results: int | None = None) -> Dict[str, List[str]]:
    max_results = max_results or config.MAX_RESULTS
    urls_rea: List[str] = []
    urls_dom: List[str] = []

    for q in _variants(address):
        if len(urls_rea) < max_results:
            for href in _ddg_text(f'{q} site:realestate.com.au', max_results):
                href = _normalize_ddg_href(href)
                if RE_URL_REA.match(href):
                    urls_rea.append(href)
                    if len(urls_rea) >= max_results: break
        time.sleep(0.6)
        if len(urls_dom) < max_results:
            for href in _ddg_text(f'{q} site:domain.com.au', max_results):
                href = _normalize_ddg_href(href)
                if RE_URL_DOM.match(href):
                    urls_dom.append(href)
                    if len(urls_dom) >= max_results: break
        if len(urls_rea) >= max_results and len(urls_dom) >= max_results:
            break

    return {"realestate": _dedupe(urls_rea)[:max_results],
            "domain":     _dedupe(urls_dom)[:max_results]}
