import os
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "2"))
DDG_REGION = os.getenv("DDG_REGION", "au-en")
CLIP_MODEL = os.getenv("CLIP_MODEL", "ViT-B/32")
PROXY_URL = os.getenv("PROXY_URL", "")