from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class PropertyItem(BaseModel):
    source: str = Field(..., description="realestate | domain")
    url: str
    listing_id: Optional[str] = None
    title: Optional[str] = None
    address: Optional[str] = None
    price: Optional[str] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    parking: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    images: List[str] = []
    features: Dict[str, str] = {}
    raw: Dict = {}

class EmbedRequest(BaseModel):
    image_urls: List[str]

class SearchResponse(BaseModel):
    realestate: List[str] = []
    domain: List[str] = []