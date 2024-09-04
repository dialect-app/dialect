class RequestError(Exception):
    """Exception raised when request fails."""


class ProviderError(Exception):
    """Exception raised when provider fails."""


class UnexpectedError(ProviderError):
    """Exception raised when provider fails."""


class APIKeyRequired(ProviderError):
    """Exception raised when provider fails."""


class APIKeyInvalid(ProviderError):
    """Exception raised when provider fails."""


class InvalidLangCode(ProviderError):
    """Exception raised when provider fails."""


class BatchSizeExceeded(ProviderError):
    """Exception raised when provider fails."""


class CharactersLimitExceeded(ProviderError):
    """Exception raised when provider fails."""


class ServiceLimitReached(ProviderError):
    """Exception raised when provider fails."""
