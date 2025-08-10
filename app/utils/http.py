import httpx
from app import config

_headers = {"User-Agent": config.USER_AGENT}

class Http:
    def __init__(self):
        self.client = httpx.AsyncClient(headers=_headers, timeout=config.HTTP_TIMEOUT, follow_redirects=True, proxies=config.PROXY_URL or None)

    async def get_text(self, url: str) -> str:
        r = await self.client.get(url)
        r.raise_for_status()
        return r.text

    async def get_bytes(self, url: str) -> bytes:
        r = await self.client.get(url)
        r.raise_for_status()
        return r.content

    async def close(self):
        await self.client.aclose()