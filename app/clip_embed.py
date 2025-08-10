from typing import List, Tuple
import torch
import clip  # from openai/CLIP
from PIL import Image
import io
from app.utils.http import Http
from app import config

_model = None
_preprocess = None

async def _load_model():
    global _model, _preprocess
    if _model is None:
        _model, _preprocess = clip.load(config.CLIP_MODEL)  # CPU by default
        _model.eval()

async def embed_image_urls(urls: List[str]) -> List[List[float]]:
    await _load_model()
    http = Http()
    try:
        imgs = []
        tensors = []
        for url in urls:
            try:
                raw = await http.get_bytes(url)
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                t = _preprocess(img).unsqueeze(0)
                tensors.append(t)
            except Exception:
                tensors.append(None)
        valid = [t for t in tensors if t is not None]
        if not valid:
            return []
        batch = torch.cat(valid, dim=0)
        with torch.no_grad():
            feats = _model.encode_image(batch)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        # Map features back to original order (None -> empty list)
        out: List[List[float]] = []
        i = 0
        for t in tensors:
            if t is None:
                out.append([])
            else:
                out.append(feats[i].cpu().tolist())
                i += 1
        return out
    finally:
        await http.close()