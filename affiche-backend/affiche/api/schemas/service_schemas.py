from typing import Optional

from pydantic import BaseModel

class ProviderTestRequest(BaseModel):
    api_key: str
    url: str = ""

class PosterCandidate(BaseModel):
    url: str
    provider: str
    rank: int = 0
    rank_score: float = 1.0
    language: Optional[str] = None
    textless: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
