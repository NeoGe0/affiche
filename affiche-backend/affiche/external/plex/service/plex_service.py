import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

from plexapi.exceptions import NotFound
from plexapi.server import PlexServer

from affiche.config.http_config import HTTP_TIMEOUT_SECONDS
from affiche.app.mediaserver.service.media_server_connector_protocol import (MediaServerConnector,
                                                                             ResetResult)
from affiche.external.media_quality import MEDIA_FIELDS, resolution_label
from affiche.external.plex.model.models import (PlexLibraryItem, PlexLibrary, PlexSeason,
                                                PlexEpisode, PlexCollection)

logger = logging.getLogger(__name__)

UPLOADED_POSTER_PREFIX = "upload://"

class PlexService(MediaServerConnector):

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self._plex: Optional[PlexServer] = None
        self._plex_lock = threading.Lock()

    @property
    def plex(self) -> PlexServer:
        if self._plex is None:
            with self._plex_lock:
                if self._plex is None:
                    self._plex = PlexServer(self.base_url, self.token,
                                            timeout=HTTP_TIMEOUT_SECONDS)
        return self._plex

    def upload_poster(self, external_id: str, poster_path: str) -> bool:
        try:
            item = self.plex.fetchItem(int(external_id))

            poster_file = Path(poster_path)
            if not poster_file.exists():
                logger.error(f"Poster file not found: {poster_path}")
                return False

            item.uploadPoster(filepath=str(poster_file))
            logger.info(f"Successfully uploaded poster for '{item.title}'")
            return True

        except NotFound:
            logger.error(f"Item with external_id {external_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error uploading poster: {e}")
            return False

    def reset_poster(self, external_id: str) -> ResetResult:
        try:
            item = self.plex.fetchItem(int(external_id))

            posters = item.posters()
            if not posters:
                logger.warning(f"No posters available for '{item.title}'")
                return ResetResult(False)

            provider_poster = next(
                (poster for poster in posters if not self._is_uploaded_poster(poster)),
                None,
            )

            if provider_poster:
                item.setPoster(provider_poster)
                logger.info(f"Reset poster for '{item.title}' to provider default")
                return ResetResult(True, self._poster_url(provider_poster))
            else:
                logger.warning(f"No provider poster available for '{item.title}'")
                return ResetResult(False)

        except NotFound:
            logger.error(f"Item with external_id {external_id} not found")
            return ResetResult(False)
        except Exception as e:
            logger.error(f"Error resetting poster: {e}")
            return ResetResult(False)

    def get_poster_url(self, external_id: str) -> Optional[str]:
        try:
            item = self.plex.fetchItem(int(external_id))
            return getattr(item, 'posterUrl', None)
        except NotFound:
            logger.warning(f"Item with external_id {external_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching poster URL for item {external_id}: {e}")
            return None

    def _poster_url(self, poster) -> Optional[str]:
        key = getattr(poster, 'key', None)
        if not key:
            return None
        if key.startswith(('http://', 'https://')):
            return key
        return self.plex.url(key, includeToken=True)

    @staticmethod
    def _is_uploaded_poster(poster) -> bool:
        return str(getattr(poster, 'ratingKey', '') or '').startswith(UPLOADED_POSTER_PREFIX)

    def get_libraries(self) -> List[PlexLibrary]:
        try:
            libraries = []
            for section in self.plex.library.sections():
                libraries.append(PlexLibrary(
                    id=str(section.key),
                    name=section.title,
                    type=section.type,
                    item_count=section.totalSize,
                    agent=section.agent,
                    language=section.language,
                    uuid=section.uuid,
                    created_at=section.createdAt,
                    updated_at=section.updatedAt))
            return libraries

        except Exception:
            logger.exception(f"Error fetching libraries")
            raise

    def get_library_items(self, library_id: int) -> List[PlexLibraryItem]:

        try:
            section = self.plex.library.sectionByID(library_id)
            return [self._to_library_item(item, library_id) for item in section.all()]

        except NotFound:
            logger.error(f"Library with ID {library_id} not found")
            raise
        except Exception:
            logger.exception(f"Error fetching library items")
            raise

    def get_recently_added_items(self, library_id: int, limit: int) -> List[PlexLibraryItem]:
        try:
            section = self.plex.library.sectionByID(library_id)
            items = section.search(sort='addedAt:desc', maxresults=limit)
            return [self._to_library_item(item, library_id) for item in items]

        except NotFound:
            logger.error(f"Library with ID {library_id} not found")
            raise
        except Exception:
            logger.exception("Error fetching recently added items")
            raise

    def _to_library_item(self, item, library_id: int) -> PlexLibraryItem:
        data = self._extract_item_metadata(item)
        return PlexLibraryItem(
            id=data['id'],
            library_id=str(library_id),
            title=data['title'],
            type=data['type'],
            year=data['year'],
            release_date=data['release_date'],
            added_at=data['added_at'],
            updated_at=data['updated_at'],
            imdb_id=data['imdb_id'],
            tmdb_id=data['tmdb_id'],
            tvdb_id=data['tvdb_id'],
            poster_url=data['poster_url'],
            **self._extract_media_info(item),
        )

    def get_library_item(self, item_key: str) -> Optional[PlexLibraryItem]:
        try:
            item = self.plex.fetchItem(int(item_key))
        except NotFound:
            logger.warning("Item %s not found on Plex", item_key)
            return None
        data = self._extract_item_metadata(item)
        return PlexLibraryItem(
            id=data['id'],
            library_id=str(data.get('library_id') or ''),
            title=data['title'],
            type=data['type'],
            year=data['year'],
            release_date=data['release_date'],
            added_at=data['added_at'],
            updated_at=data['updated_at'],
            imdb_id=data['imdb_id'],
            tmdb_id=data['tmdb_id'],
            tvdb_id=data['tvdb_id'],
            poster_url=data['poster_url'],
            **self._extract_media_info(item),
        )

    def get_collections(self, library_id: str) -> List[PlexCollection]:
        try:
            section = self.plex.library.sectionByID(int(library_id))
        except NotFound:
            logger.error("Library with ID %s not found", library_id)
            raise

        collections = []
        for collection in section.collections():
            collections.append(PlexCollection(
                id=str(collection.ratingKey),
                library_id=str(library_id),
                title=collection.title,
                sort_title=getattr(collection, 'titleSort', None),
                child_count=getattr(collection, 'childCount', None),
                added_at=getattr(collection, 'addedAt', None),
                updated_at=getattr(collection, 'updatedAt', None),
                poster_url=getattr(collection, 'posterUrl', None),
                member_external_ids=self._collection_members(collection),
            ))
        return collections

    @staticmethod
    def _collection_members(collection) -> List[str]:
        try:
            return [str(item.ratingKey) for item in collection.items()]
        except Exception:
            logger.warning("Could not read members of collection '%s'", collection.title,
                           exc_info=True)
            return []

    def create_collection(self, library_external_id: str, title: str,
                          item_external_ids: List[str]) -> Optional[str]:
        try:
            section = self.plex.library.sectionByID(int(library_external_id))
            items = [self.plex.fetchItem(int(external_id)) for external_id in item_external_ids]
            collection = self.plex.createCollection(title=title, section=section, items=items)
            return str(collection.ratingKey)
        except Exception:
            logger.exception("Failed to create Plex collection '%s'", title)
            return None

    def rename_collection(self, external_id: str, title: str) -> bool:
        try:
            self.plex.fetchItem(int(external_id)).editTitle(title)
            return True
        except Exception:
            logger.exception("Failed to rename Plex collection %s", external_id)
            return False

    def delete_collection(self, external_id: str) -> bool:
        try:
            self.plex.fetchItem(int(external_id)).delete()
            return True
        except Exception:
            logger.exception("Failed to delete Plex collection %s", external_id)
            return False

    def add_to_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        try:
            collection = self.plex.fetchItem(int(external_id))
            collection.addItems([self.plex.fetchItem(int(i)) for i in item_external_ids])
            return True
        except Exception:
            logger.exception("Failed to add items to Plex collection %s", external_id)
            return False

    def remove_from_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        try:
            collection = self.plex.fetchItem(int(external_id))
            collection.removeItems([self.plex.fetchItem(int(i)) for i in item_external_ids])
            return True
        except Exception:
            logger.exception("Failed to remove items from Plex collection %s", external_id)
            return False

    def get_show_seasons(self, show_key: str, library_id: int) -> List[PlexSeason]:
        try:
            show = self.plex.fetchItem(int(show_key))

            if show.type != 'show':
                logger.warning(f"Item {show_key} is not a show, skipping seasons")
                return []

            seasons = []
            for season in show.seasons():
                season_data = self._extract_season_metadata(season, show_key, library_id)
                seasons.append(PlexSeason(**season_data))

            return seasons

        except NotFound:
            logger.error(f"Show with key {show_key} not found")
            raise
        except Exception:
            logger.exception(f"Error fetching seasons for show {show_key}")
            raise

    def _extract_season_metadata(self, season, show_id: str, library_id: int) -> Dict[str, Any]:
        metadata = {
            'id': str(season.ratingKey),
            'show_id': show_id,
            'library_id': str(library_id),
            'season_number': season.index,
            'title': season.title,
            'added_at': getattr(season, 'addedAt', None),
            'updated_at': getattr(season, 'updatedAt', None),
            'imdb_id': None,
            'tmdb_id': None,
            'tvdb_id': None,
            'poster_url': getattr(season, 'posterUrl', None),
        }

        try:
            guids = getattr(season, 'guids', [])
            for guid in guids:
                guid_id = guid.id.lower()
                if 'imdb://' in guid_id:
                    metadata['imdb_id'] = guid_id.split('imdb://')[1]
                elif 'tmdb://' in guid_id:
                    metadata['tmdb_id'] = guid_id.split('tmdb://')[1]
                elif 'tvdb://' in guid_id:
                    metadata['tvdb_id'] = guid_id.split('tvdb://')[1]
        except Exception as e:
            logger.warning(f"Could not extract external IDs for season {season.title}: {e}")

        return metadata

    def get_show_episodes(self, show_key: str, library_id: int) -> List[PlexEpisode]:
        try:
            show = self.plex.fetchItem(int(show_key))
            if show.type != 'show':
                logger.warning(f"Item {show_key} is not a show, skipping episodes")
                return []

            episodes = []
            for episode in show.episodes():
                episodes.append(PlexEpisode(
                    **self._extract_episode_metadata(episode, library_id),
                    **self._extract_media_info(episode),
                ))
            return episodes

        except NotFound:
            logger.error(f"Show with key {show_key} not found")
            raise
        except Exception:
            logger.exception(f"Error fetching episodes for show {show_key}")
            raise

    def _extract_episode_metadata(self, episode, library_id: int) -> Dict[str, Any]:
        metadata = {
            'id': str(episode.ratingKey),
            'season_external_id': str(getattr(episode, 'parentRatingKey', '')),
            'library_id': str(library_id),
            'season_number': getattr(episode, 'parentIndex', 0) or 0,
            'episode_number': getattr(episode, 'index', 0) or 0,
            'title': episode.title,
            'air_date': getattr(episode, 'originallyAvailableAt', None),
            'added_at': getattr(episode, 'addedAt', None),
            'updated_at': getattr(episode, 'updatedAt', None),
            'imdb_id': None,
            'tmdb_id': None,
            'tvdb_id': None,
        }

        try:
            for guid in getattr(episode, 'guids', []):
                guid_id = guid.id.lower()
                if 'imdb://' in guid_id:
                    metadata['imdb_id'] = guid_id.split('imdb://')[1]
                elif 'tmdb://' in guid_id:
                    metadata['tmdb_id'] = guid_id.split('tmdb://')[1]
                elif 'tvdb://' in guid_id:
                    metadata['tvdb_id'] = guid_id.split('tvdb://')[1]
        except Exception as e:
            logger.warning(f"Could not extract external IDs for episode {episode.title}: {e}")

        return metadata

    def _extract_item_metadata(self, item) -> Dict[str, Any]:

        metadata = {
            'id': str(item.ratingKey),
            'title': item.title,
            'type': item.type,
            'year': getattr(item, 'year', None),
            'release_date': getattr(item, 'originallyAvailableAt', None),
            'rating': getattr(item, 'rating', None),
            'added_at': getattr(item, 'addedAt', None),
            'updated_at': getattr(item, 'updatedAt', None),
            'imdb_id': None,
            'tmdb_id': None,
            'tvdb_id': None,
            'library_id': getattr(item, 'librarySectionID', None),
            'poster_url': getattr(item, 'posterUrl', None),
        }

        try:
            guids = getattr(item, 'guids', [])
            for guid in guids:
                guid_id = guid.id.lower()

                if 'imdb://' in guid_id:
                    metadata['imdb_id'] = guid_id.split('imdb://')[1]
                elif 'tmdb://' in guid_id:
                    metadata['tmdb_id'] = guid_id.split('tmdb://')[1]
                elif 'tvdb://' in guid_id:
                    metadata['tvdb_id'] = guid_id.split('tvdb://')[1]

            if hasattr(item, 'guid'):
                guid_lower = item.guid.lower()
                if 'imdb' in guid_lower and not metadata['imdb_id']:
                    parts = guid_lower.split('://')
                    if len(parts) > 1:
                        metadata['imdb_id'] = parts[1].split('?')[0]

        except Exception as e:
            logger.warning(f"Could not extract external IDs for {item.title}: {e}")

        return metadata

    def _extract_media_info(self, item) -> Dict[str, Any]:
        empty = {field: None for field in MEDIA_FIELDS}
        if getattr(item, 'type', None) not in ('movie', 'episode'):
            return empty
        try:
            media_list = getattr(item, 'media', None) or []
            if not media_list:
                return empty
            media = media_list[0]
            parts = getattr(media, 'parts', None) or []
            part = parts[0] if parts else None

            width = getattr(media, 'width', None)
            height = getattr(media, 'height', None)
            bitrate_kbps = getattr(media, 'bitrate', None)

            return {
                'media_resolution': resolution_label(width, height),
                'media_width': width,
                'media_height': height,
                'video_codec': getattr(media, 'videoCodec', None),
                'audio_codec': getattr(media, 'audioCodec', None),
                'audio_channels': getattr(media, 'audioChannels', None),
                'media_container': getattr(media, 'container', None),
                'media_bitrate': bitrate_kbps * 1000 if bitrate_kbps else None,
                'media_size_bytes': getattr(part, 'size', None) if part else None,
            }
        except Exception:
            logger.warning("Could not extract media info for '%s'", getattr(item, 'title', '?'),
                           exc_info=True)
            return empty

    def refresh_metadata(self, item_key: str) -> bool:

        try:
            item = self.plex.fetchItem(int(item_key))
            item.refresh()
            logger.info(f"Successfully refreshed metadata for '{item.title}'")
            return True

        except NotFound:
            logger.error(f"Item with key {item_key} not found")
            return False
        except Exception as e:
            logger.error(f"Error refreshing metadata: {e}")
            return False

    def get_server_info(self) -> Dict[str, Any]:

        try:
            return {
                'friendly_name': self.plex.friendlyName,
                'platform': self.plex.platform,
                'platform_version': self.plex.platformVersion,
                'version': self.plex.version,
                'machine_identifier': self.plex.machineIdentifier,
                'my_plex_username': getattr(self.plex, 'myPlexUsername', None),
            }
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            raise
