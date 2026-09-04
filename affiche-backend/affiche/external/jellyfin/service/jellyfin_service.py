import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

from affiche.config.http_config import HTTP_TIMEOUT
from affiche.app.mediaserver.service.media_server_connector_protocol import (MediaServerConnector,
                                                                             ResetResult)
from affiche.external.media_quality import MEDIA_FIELDS, resolution_label
from affiche.external.jellyfin.model.models import (JellyfinLibraryItem, JellyfinLibrary,
                                                   JellyfinSeason, JellyfinEpisode,
                                                   JellyfinCollection)

logger = logging.getLogger(__name__)

class JellyfinService(MediaServerConnector):

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._headers = {
            'X-Emby-Token': api_key,
            'Accept': 'application/json',
        }

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self._headers, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Any = None, content_type: str = 'application/json',
              params: Optional[Dict] = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        headers = {**self._headers, 'Content-Type': content_type}
        response = requests.post(url, headers=headers, data=data, params=params,
                                 timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response

    def _delete(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self._headers, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response

    def upload_poster(self, external_id: str, poster_path: str) -> bool:
        try:
            poster_file = Path(poster_path)
            if not poster_file.exists():
                logger.error(f"Poster file not found: {poster_path}")
                return False

            with open(poster_file, 'rb') as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode('utf-8')

            self._post(
                f"/Items/{external_id}/Images/Primary",
                data=base64_data,
                content_type='image/jpeg'
            )
            logger.info(f"Successfully uploaded poster for item {external_id}")
            return True

        except requests.HTTPError as e:
            logger.error(f"HTTP error uploading poster for item {external_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error uploading poster for item {external_id}: {e}")
            return False

    def reset_poster(self, external_id: str) -> ResetResult:
        try:
            self._delete(f"/Items/{external_id}/Images/Primary")
            self.refresh_metadata(external_id)
            logger.info(f"Successfully reset poster for item {external_id}")
            return ResetResult(True, self._get_poster_url(external_id))

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No custom poster to reset for item {external_id}")
                return ResetResult(True, self._get_poster_url(external_id))
            logger.error(f"HTTP error resetting poster for item {external_id}: {e}")
            return ResetResult(False)
        except Exception as e:
            logger.error(f"Error resetting poster for item {external_id}: {e}")
            return ResetResult(False)

    def get_poster_url(self, external_id: str) -> Optional[str]:
        return self._get_poster_url(external_id)

    def get_libraries(self) -> List[JellyfinLibrary]:
        try:
            libraries = []
            data = self._get("/Library/VirtualFolders")

            for folder in data:
                collection_type = folder.get('CollectionType', '')
                library_type = self._map_collection_type(collection_type)

                if library_type not in ('movie', 'show'):
                    continue

                item_ids = folder.get('ItemId')
                item_count = 0
                if item_ids:
                    count_data = self._get("/Items/Counts", params={'ParentId': item_ids})
                    if library_type == 'movie':
                        item_count = count_data.get('MovieCount', 0)
                    elif library_type == 'show':
                        item_count = count_data.get('SeriesCount', 0)

                libraries.append(JellyfinLibrary(
                    id=folder.get('ItemId', ''),
                    name=folder.get('Name', ''),
                    type=library_type,
                    item_count=item_count,
                    language=folder.get('LibraryOptions', {}).get('PreferredMetadataLanguage', 'en'),
                ))

            return libraries

        except Exception:
            logger.exception("Error fetching Jellyfin libraries")
            raise

    _ITEM_QUERY = {
        'Recursive': 'true',
        'Fields': 'ProviderIds,DateCreated,PremiereDate,MediaSources',
        'IncludeItemTypes': 'Movie,Series',
    }

    def get_library_items(self, library_id: str) -> List[JellyfinLibraryItem]:
        try:
            data = self._get("/Items", params={**self._ITEM_QUERY, 'ParentId': library_id})
            return [JellyfinLibraryItem(**self._extract_item_metadata(item, library_id))
                    for item in data.get('Items', [])]

        except Exception:
            logger.exception(f"Error fetching library items for library {library_id}")
            raise

    def get_recently_added_items(self, library_id: str, limit: int) -> List[JellyfinLibraryItem]:
        try:
            data = self._get("/Items", params={
                **self._ITEM_QUERY,
                'ParentId': library_id,
                'SortBy': 'DateCreated',
                'SortOrder': 'Descending',
                'Limit': limit,
            })
            return [JellyfinLibraryItem(**self._extract_item_metadata(item, library_id))
                    for item in data.get('Items', [])]

        except Exception:
            logger.exception("Error fetching recently added items for library %s", library_id)
            raise

    def get_library_item(self, item_id: str, library_id: str) -> Optional[JellyfinLibraryItem]:
        data = self._get("/Items", params={
            'Ids': item_id,
            'Fields': 'ProviderIds,DateCreated,PremiereDate,MediaSources',
        })
        items = data.get('Items', [])
        if not items:
            logger.warning("Item %s not found on Jellyfin", item_id)
            return None
        return JellyfinLibraryItem(**self._extract_item_metadata(items[0], library_id))

    def get_collections(self, library_id: str) -> List[JellyfinCollection]:
        try:
            data = self._get("/Items", params={
                'IncludeItemTypes': 'BoxSet',
                'Recursive': 'true',
                'Fields': 'DateCreated,SortName,ChildCount',
            })
        except Exception:
            logger.exception("Error fetching Jellyfin collections")
            raise

        collections = []
        for boxset in data.get('Items', []):
            boxset_id = boxset.get('Id')
            collections.append(JellyfinCollection(
                id=boxset_id,
                library_id=library_id,
                title=boxset.get('Name', 'Untitled'),
                sort_title=boxset.get('SortName'),
                child_count=boxset.get('ChildCount'),
                added_at=self._parse_date(boxset.get('DateCreated')),
                poster_url=self._get_poster_url(boxset_id),
                member_external_ids=self._collection_members(boxset_id),
            ))
        return collections

    def _collection_members(self, boxset_id: str) -> List[str]:
        try:
            data = self._get("/Items", params={'ParentId': boxset_id, 'Recursive': 'true'})
            return [item['Id'] for item in data.get('Items', []) if item.get('Id')]
        except Exception:
            logger.warning("Could not read members of BoxSet %s", boxset_id, exc_info=True)
            return []

    def create_collection(self, library_external_id: str, title: str,
                          item_external_ids: List[str]) -> Optional[str]:
        try:
            response = self._post("/Collections", params={
                'Name': title,
                'Ids': ','.join(item_external_ids),
            })
            return (response.json() or {}).get('Id')
        except Exception:
            logger.exception("Failed to create Jellyfin collection '%s'", title)
            return None

    def rename_collection(self, external_id: str, title: str) -> bool:
        try:
            data = self._get("/Items", params={'Ids': external_id, 'Fields': 'SortName,Overview'})
            items = data.get('Items', [])
            if not items:
                logger.warning("Collection %s not found on Jellyfin", external_id)
                return False

            payload = {**items[0], 'Name': title}
            self._post(f"/Items/{external_id}", data=json.dumps(payload))
            return True
        except Exception:
            logger.exception("Failed to rename Jellyfin collection %s", external_id)
            return False

    def delete_collection(self, external_id: str) -> bool:
        try:
            self._delete(f"/Items/{external_id}")
            return True
        except Exception:
            logger.exception("Failed to delete Jellyfin collection %s", external_id)
            return False

    def add_to_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        try:
            self._post(f"/Collections/{external_id}/Items",
                       params={'Ids': ','.join(item_external_ids)})
            return True
        except Exception:
            logger.exception("Failed to add items to Jellyfin collection %s", external_id)
            return False

    def remove_from_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        try:
            self._delete(f"/Collections/{external_id}/Items",
                         params={'Ids': ','.join(item_external_ids)})
            return True
        except Exception:
            logger.exception("Failed to remove items from Jellyfin collection %s", external_id)
            return False

    def get_show_seasons(self, show_id: str, library_id: str) -> List[JellyfinSeason]:
        try:
            seasons = []
            params = {
                'ParentId': show_id,
                'IncludeItemTypes': 'Season',
                'Fields': 'ProviderIds,DateCreated',
            }

            data = self._get("/Items", params=params)

            for season in data.get('Items', []):
                season_data = self._extract_season_metadata(season, show_id, library_id)
                seasons.append(JellyfinSeason(**season_data))

            return seasons

        except Exception:
            logger.exception(f"Error fetching seasons for show {show_id}")
            raise

    def get_show_episodes(self, show_id: str, library_id: str) -> List[JellyfinEpisode]:
        try:
            params = {
                'ParentId': show_id,
                'Recursive': 'true',
                'IncludeItemTypes': 'Episode',
                'Fields': 'ProviderIds,DateCreated,PremiereDate,MediaSources',
            }
            data = self._get("/Items", params=params)
            return [JellyfinEpisode(**self._extract_episode_metadata(ep, library_id))
                    for ep in data.get('Items', [])]

        except Exception:
            logger.exception(f"Error fetching episodes for show {show_id}")
            raise

    def _extract_episode_metadata(self, episode: Dict[str, Any], library_id: str) -> Dict[str, Any]:
        provider_ids = episode.get('ProviderIds', {})
        return {
            'id': episode.get('Id', ''),
            'season_external_id': episode.get('SeasonId', '') or episode.get('ParentId', ''),
            'library_id': library_id,
            'season_number': episode.get('ParentIndexNumber', 0) or 0,
            'episode_number': episode.get('IndexNumber', 0) or 0,
            'title': episode.get('Name', ''),
            'air_date': self._parse_date(episode.get('PremiereDate')),
            'added_at': self._parse_date(episode.get('DateCreated')),
            'updated_at': self._parse_date(episode.get('DateCreated')),
            'imdb_id': provider_ids.get('Imdb'),
            'tmdb_id': provider_ids.get('Tmdb'),
            'tvdb_id': provider_ids.get('Tvdb'),
            **self._extract_media_info(episode),
        }

    def refresh_metadata(self, item_id: str) -> bool:
        try:
            self._post(f"/Items/{item_id}/Refresh", data=None)
            logger.info(f"Successfully refreshed metadata for item {item_id}")
            return True

        except requests.HTTPError as e:
            logger.error(f"HTTP error refreshing metadata for item {item_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error refreshing metadata for item {item_id}: {e}")
            return False

    def get_server_info(self) -> Dict[str, Any]:
        try:
            data = self._get("/System/Info")
            return {
                'friendly_name': data.get('ServerName', ''),
                'platform': data.get('OperatingSystem', ''),
                'platform_version': data.get('OperatingSystemDisplayName', ''),
                'version': data.get('Version', ''),
                'machine_identifier': data.get('Id', ''),
            }
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            raise

    def _map_collection_type(self, collection_type: str) -> str:
        mapping = {
            'movies': 'movie',
            'tvshows': 'show',
        }
        return mapping.get(collection_type.lower(), collection_type)

    def _extract_item_metadata(self, item: Dict[str, Any], library_id: str) -> Dict[str, Any]:
        provider_ids = item.get('ProviderIds', {})
        item_type = item.get('Type', '').lower()

        if item_type == 'series':
            item_type = 'show'

        metadata = {
            'id': item.get('Id', ''),
            'library_id': library_id,
            'title': item.get('Name', ''),
            'type': item_type,
            'year': item.get('ProductionYear'),
            'release_date': self._parse_date(item.get('PremiereDate')),
            'added_at': self._parse_date(item.get('DateCreated')),
            'updated_at': self._parse_date(item.get('DateCreated')),
            'imdb_id': provider_ids.get('Imdb'),
            'tmdb_id': provider_ids.get('Tmdb'),
            'tvdb_id': provider_ids.get('Tvdb'),
            'poster_url': self._get_poster_url(item.get('Id')),
            **self._extract_media_info(item),
        }

        return metadata

    def _extract_media_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        empty = {field: None for field in MEDIA_FIELDS}
        if item.get('Type', '').lower() not in ('movie', 'episode'):
            return empty
        try:
            sources = item.get('MediaSources') or []
            if not sources:
                return empty
            source = sources[0]
            streams = source.get('MediaStreams') or []
            video = next((s for s in streams if s.get('Type') == 'Video'), {})
            audio = next((s for s in streams if s.get('Type') == 'Audio'), {})

            width = video.get('Width')
            height = video.get('Height')

            return {
                'media_resolution': resolution_label(width, height),
                'media_width': width,
                'media_height': height,
                'video_codec': video.get('Codec'),
                'audio_codec': audio.get('Codec'),
                'audio_channels': audio.get('Channels'),
                'media_container': source.get('Container'),
                'media_bitrate': source.get('Bitrate'),
                'media_size_bytes': source.get('Size'),
            }
        except Exception:
            logger.warning("Could not extract media info for '%s'", item.get('Name', '?'),
                           exc_info=True)
            return empty

    def _extract_season_metadata(self, season: Dict[str, Any], show_id: str, library_id: str) -> Dict[str, Any]:
        provider_ids = season.get('ProviderIds', {})

        metadata = {
            'id': season.get('Id', ''),
            'show_id': show_id,
            'library_id': library_id,
            'season_number': season.get('IndexNumber', 0),
            'title': season.get('Name', ''),
            'added_at': self._parse_date(season.get('DateCreated')),
            'updated_at': self._parse_date(season.get('DateCreated')),
            'imdb_id': provider_ids.get('Imdb'),
            'tmdb_id': provider_ids.get('Tmdb'),
            'tvdb_id': provider_ids.get('Tvdb'),
            'poster_url': self._get_poster_url(season.get('Id')),
        }

        return metadata

    def _get_poster_url(self, item_id: str) -> Optional[str]:
        if not item_id:
            return None
        return f"{self.base_url}/Items/{item_id}/Images/Primary"

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
