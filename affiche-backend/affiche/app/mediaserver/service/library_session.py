from contextlib import contextmanager
from typing import Callable, Iterator, Tuple

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.service.library_repository import LibraryRepository

@contextmanager
def library_session(
        session_factory: Callable[[], Session]
) -> Iterator[Tuple[LibraryRepository, Session]]:
    session = session_factory()
    try:
        yield LibraryRepository(session), session
    finally:
        session.close()
