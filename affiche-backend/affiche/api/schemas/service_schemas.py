from pydantic import BaseModel

class ProviderTestRequest(BaseModel):
    api_key: str
    url: str = ""

class PosterCandidate(BaseModel):
    url: str
    provider: str
    rank: int = 0
    rank_score: float = 1.0
