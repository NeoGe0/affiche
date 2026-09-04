class ServiceConfigurationNotFoundError(Exception):
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Service configuration '{service_name}' not found")

class MediaServerNotFoundError(Exception):
    def __init__(self, id: int):
        super().__init__(f"Media server with id '{id}' not found")

class MediaServerUnreachableError(Exception):

    def __init__(self, target: str = "the media server", media_server_id: int = None):
        self.media_server_id = media_server_id
        super().__init__(f"Failed to connect to {target}")

class MediaServerCredentialsRejectedError(Exception):

    def __init__(self, target: str, credential: str = "token"):
        super().__init__(f"{target} rejected that {credential}")

class NoProvidersConfiguredError(Exception):

    def __init__(self):
        super().__init__(
            "No poster providers are configured. "
            "Please enable at least one provider (TMDB, TVDB, or Fanart)."
        )

class UnknownProviderError(Exception):

    def __init__(self, provider: str, valid_providers: list[str]):
        self.provider = provider
        self.valid_providers = valid_providers
        super().__init__(
            f"Unknown provider: {provider}. Valid options: {', '.join(valid_providers)}"
        )

class ProviderConnectionError(Exception):

    def __init__(self, provider: str, reason: str = None):
        self.provider = provider
        message = f"Failed to connect to {provider.upper()}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
