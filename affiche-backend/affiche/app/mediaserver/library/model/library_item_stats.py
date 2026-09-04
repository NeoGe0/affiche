from pydantic import BaseModel

class LibraryItemStats(BaseModel):
    total: int = 0
    processed: int = 0
    unprocessed: int = 0
    errors: int = 0
    locked: int = 0
    uploaded: int = 0

    def __add__(self, other: 'LibraryItemStats') -> 'LibraryItemStats':
        return LibraryItemStats(**{
            field: getattr(self, field) + getattr(other, field)
            for field in LibraryItemStats.model_fields
        })
