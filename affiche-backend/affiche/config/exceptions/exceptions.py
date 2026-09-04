class NotFoundError(Exception):
    pass

class LibraryNotFoundException(NotFoundError):
    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Library with id: {id} not found"

class LibraryItemNotFoundException(NotFoundError):
    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Library item with id: {id} not found"

class ItemMissingOnMediaServerException(NotFoundError):

    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Item {id} could not be synced (not found on the media server)"

class LibraryCollectionNotFoundException(NotFoundError):
    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Library collection with id: {id} not found"

class StyleProfileNotFoundException(NotFoundError):
    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Style profile with id: {id} not found"

class NotificationTargetNotFoundException(NotFoundError):
    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Notification target with id: {id} not found"

class LibraryDisabledException(Exception):

    def __init__(self, id: int):
        super().__init__(id)
        self.message = f"Library with id: {id} is not enabled"
