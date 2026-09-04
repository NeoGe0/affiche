import hashlib
import logging
import shutil
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

Thumbnailer = Callable[[bytes], bytes]

THUMB_SUFFIX = "_thumb"

SOURCE_SUFFIX = "_source"

def poster_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class FileStoreService:
    def __init__(
            self,
            root_dir: str | Path,
            shard_levels: int = 2,
            shard_size: int = 2,
            default_extension: str = ".jpg",
            thumbnailer: Optional[Thumbnailer] = None,
            kind: str = "posters",
    ):
        self.root_dir = Path(root_dir)
        self.shard_levels = shard_levels
        self.shard_size = shard_size
        self.default_extension = default_extension
        self._thumbnailer = thumbnailer
        self.kind = kind

    def _library_path(self, library: int) -> Path:
        return self.root_dir / "libraries" / str(library)

    def _sharded_path(
            self,
            library: int,
            item_id: int,
            extension: Optional[str],
            season_number: Optional[int] = None,
            thumb: bool = False,
            suffix: str = "",
    ) -> Path:
        digest = hashlib.sha1(str(item_id).encode("utf-8")).hexdigest()

        shards = [
            digest[i * self.shard_size: (i + 1) * self.shard_size]
            for i in range(self.shard_levels)
        ]

        ext = extension or self.default_extension
        suffix = THUMB_SUFFIX if thumb else suffix

        base_path = self._library_path(library) / self.kind / Path(*shards)

        if season_number is not None:
            return base_path / str(item_id) / f"S{season_number:02d}{suffix}{ext}"

        return base_path / f"{item_id}{suffix}{ext}"

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("wb") as f:
            f.write(data)

        tmp_path.replace(path)

    def save(
            self,
            library: int,
            item_id: int,
            data: bytes,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Path:
        path = self._sharded_path(library, item_id, extension, season_number)
        self._atomic_write(path, data)
        self._write_thumbnail(library, item_id, data, extension, season_number)
        return path

    def _write_thumbnail(
            self,
            library: int,
            item_id: int,
            data: bytes,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Optional[Path]:
        if self._thumbnailer is None:
            return None

        path = self._sharded_path(library, item_id, extension, season_number, thumb=True)
        try:
            self._atomic_write(path, self._thumbnailer(data))
            return path
        except Exception:
            logger.warning("Could not build thumbnail for %s/%s", library, item_id, exc_info=True)
            path.unlink(missing_ok=True)
            return None

    def preserve_source(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bool:
        source_path = self._sharded_path(library, item_id, extension, season_number,
                                         suffix=SOURCE_SUFFIX)
        if source_path.exists():
            return False

        current = self._sharded_path(library, item_id, extension, season_number)
        try:
            data = current.read_bytes()
        except OSError:
            return False

        self._atomic_write(source_path, data)
        return True

    def fetch_source(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bytes:
        path = self._sharded_path(library, item_id, extension, season_number,
                                  suffix=SOURCE_SUFFIX)
        if not path.exists():
            raise FileNotFoundError(f"Source poster not found: {library}/{item_id}")
        return path.read_bytes()

    def source_version(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        try:
            stat = self._sharded_path(library, item_id, extension, season_number,
                                      suffix=SOURCE_SUFFIX).stat()
        except OSError:
            return None
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"

    def fetch(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bytes:
        path = self._sharded_path(library, item_id, extension, season_number)

        if not path.exists():
            if season_number is not None:
                raise FileNotFoundError(f"Season poster not found: {library}/{item_id}/S{season_number:02d}")
            raise FileNotFoundError(f"Poster not found: {library}/{item_id}")

        return path.read_bytes()

    def fetch_thumbnail(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bytes:
        poster_path = self._sharded_path(library, item_id, extension, season_number)
        thumb_path = self._sharded_path(library, item_id, extension, season_number, thumb=True)

        try:
            poster_stat = poster_path.stat()
        except OSError:
            if season_number is not None:
                raise FileNotFoundError(
                    f"Season poster not found: {library}/{item_id}/S{season_number:02d}")
            raise FileNotFoundError(f"Poster not found: {library}/{item_id}")

        try:
            if thumb_path.stat().st_mtime_ns >= poster_stat.st_mtime_ns:
                return thumb_path.read_bytes()
        except OSError:
            pass

        data = poster_path.read_bytes()
        if self._write_thumbnail(library, item_id, data, extension, season_number) is None:
            return data
        return thumb_path.read_bytes()

    def thumbnail_version(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        return self.version(library, item_id, extension, season_number)

    def digest(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        try:
            return poster_digest(self.fetch(library, item_id, extension, season_number))
        except FileNotFoundError:
            return None

    def exists(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bool:
        return self._sharded_path(library, item_id, extension, season_number).exists()

    def version(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Optional[str]:
        try:
            stat = self._sharded_path(library, item_id, extension, season_number).stat()
        except OSError:
            return None
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"

    def path(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> Path:
        return self._sharded_path(library, item_id, extension, season_number)

    def delete_library(self, library: int) -> bool:
        path = self._library_path(library)
        if not path.is_dir():
            return False
        shutil.rmtree(path)
        return True

    def delete(
            self,
            library: int,
            item_id: int,
            extension: Optional[str] = None,
            season_number: Optional[int] = None,
    ) -> bool:
        path = self._sharded_path(library, item_id, extension, season_number)
        for extra in (dict(thumb=True), dict(suffix=SOURCE_SUFFIX)):
            self._sharded_path(library, item_id, extension, season_number,
                               **extra).unlink(missing_ok=True)
        if path.exists():
            path.unlink()
            return True
        return False
