class ScraperNotFoundError(Exception):
    """Raised when no scraper can handle a given URL."""


class ScraperError(Exception):
    """Raised when a scraper fails to fetch or parse data."""
