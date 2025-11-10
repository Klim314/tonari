class ServiceError(Exception):
    """Base exception for service layer failures."""


class NotFoundError(ServiceError):
    """Raised when an entity is not found."""


class WorkNotFoundError(NotFoundError):
    """Raised when a work lookup fails."""


class ChapterNotFoundError(NotFoundError):
    """Raised when a chapter lookup fails."""


class ChapterScrapeError(ServiceError):
    """Raised when a chapter scrape request cannot be fulfilled."""
