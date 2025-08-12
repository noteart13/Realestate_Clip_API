# app/utils/http.py
import asyncio, random, time
from urllib.parse import urlparse
import httpx
from app import config

# ---- Config (đọc từ .env nếu có, có giá trị mặc định) -----------------------
HTTP_TIMEOUT_S        = float(getattr(config, "HTTP_TIMEOUT", 20))     # tổng timeout
HTTP_MAX_RETRIES      = int(getattr(config, "HTTP_MAX_RETRIES", 5))
HTTP_BACKOFF_BASE     = float(getattr(config, "HTTP_BACKOFF_BASE", 1.8))
HTTP_RATE_GAP_DEFAULT = float(getattr(config, "HTTP_RATE_GAP_DEFAULT", 1.5))

_RATE_GAP_BY_HOST = {
    "www.realestate.com.au": 2.5,
    "realestate.com.au":     2.5,
    "www.domain.com.au":     2.5,
    "domain.com.au":         2.5,
}
# -----------------------------------------------------------------------------

class Http:
    """HTTP client có retry + backoff + rate-gap theo host."""
    _last_hit: dict[str, float] = {}  # host -> last monotonic time

    def __init__(self):
        proxies = None
        if getattr(config, "PROXY_URL", ""):
            proxies = {"http": config.PROXY_URL, "https": config.PROXY_URL}

        self.cookies = httpx.Cookies()
        # QUAN TRỌNG: dùng 1 con số cho timeout (tránh lỗi thiếu 'pool')
        self.client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_S,
            follow_redirects=True,
            http2=True,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
            cookies=self.cookies,
            proxies=proxies,
        )

    async def _respect_rate_gap(self, host: str):
        gap = _RATE_GAP_BY_HOST.get(host, HTTP_RATE_GAP_DEFAULT)
        now = time.monotonic()
        last = self._last_hit.get(host, 0.0)
        wait = (last + gap) - now
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_hit[host] = time.monotonic()

    async def _get(self, url: str, *, referer: str | None = None) -> httpx.Response:
        headers = {}
        if referer:
            headers["Referer"] = referer
        # thỉnh thoảng đổi Accept-Language cho “giống người”
        if random.random() < 0.25:
            headers["Accept-Language"] = random.choice(["en-US,en;q=0.9", "en-AU,en;q=0.9"])
        return await self.client.get(url, headers=headers)

    async def get_text(self, url: str, *, max_retries: int | None = None, referer: str | None = None) -> str:
        host = urlparse(url).netloc.lower()
        await self._respect_rate_gap(host)

        retries = HTTP_MAX_RETRIES if max_retries is None else max_retries
        attempt = 0
        last_exc: Exception | None = None

        while attempt <= retries:
            try:
                r = await self._get(url, referer=referer)

                # 429/403/503 -> backoff và thử lại
                if r.status_code in (429, 403, 503):
                    ra = r.headers.get("Retry-After")
                    sleep_s = float(ra) if (ra and ra.isdigit()) else (HTTP_BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(sleep_s)
                    attempt += 1
                    continue

                r.raise_for_status()
                return r.text

            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                last_exc = e
                await asyncio.sleep((HTTP_BACKOFF_BASE ** attempt) + random.uniform(0, 0.5))
                attempt += 1
                continue
            except httpx.HTTPStatusError as e:
                last_exc = e
                # các mã “mềm” đã xử lý ở trên; còn lại ném ra luôn
                raise

        raise last_exc or RuntimeError("Upstream failed after retries")

    async def get_bytes(self, url: str, *, max_retries: int | None = None, referer: str | None = None) -> bytes:
        host = urlparse(url).netloc.lower()
        await self._respect_rate_gap(host)

        retries = HTTP_MAX_RETRIES if max_retries is None else max_retries
        attempt = 0
        last_exc: Exception | None = None

        while attempt <= retries:
            try:
                r = await self._get(url, referer=referer)

                if r.status_code in (429, 403, 503):
                    ra = r.headers.get("Retry-After")
                    sleep_s = float(ra) if (ra and ra.isdigit()) else (HTTP_BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(sleep_s)
                    attempt += 1
                    continue

                r.raise_for_status()
                return r.content

            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                last_exc = e
                await asyncio.sleep((HTTP_BACKOFF_BASE ** attempt) + random.uniform(0, 0.5))
                attempt += 1
                continue
            except httpx.HTTPStatusError as e:
                last_exc = e
                raise

        raise last_exc or RuntimeError("Upstream failed after retries")

    async def close(self):
        await self.client.aclose()
