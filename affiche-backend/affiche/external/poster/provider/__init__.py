from affiche.external.poster.provider.base_provider import ExternalProvider
from affiche.external.poster.provider.tmdb import TMDBClient
from affiche.external.poster.provider.tvdb import TVDBClient
from affiche.external.poster.provider.fanart import FanartClient
from affiche.external.poster.provider.mediux import MediuxClient
from affiche.external.poster.provider.tvmaze import TVmazeClient
from affiche.external.poster.provider.shoko import ShokoClient

__all__ = [
    "ExternalProvider",
    "TMDBClient",
    "TVDBClient",
    "FanartClient",
    "MediuxClient",
    "TVmazeClient",
    "ShokoClient",
]
