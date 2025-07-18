from functools import lru_cache
from plexapi.server import PlexServer
import logging

log = logging.getLogger("trailarr.plex")

class PlexExtras:
    """Tiny wrapper that answers: does Plex already have a trailer?"""

    def __init__(self, url: str, token: str):
        self.server = PlexServer(url, token)

    @lru_cache(maxsize=4096)
    def has_trailer(self, tmdb_id: str) -> bool:
        """Return True if Plex shows at least one trailer extra for this TMDb ID.

        The Plex API exposes trailers as extras with ``type`` set to ``"clip"``
        and ``subtype`` set to ``"trailer"``. Older logic only checked that the
        ``type`` was ``"trailer"`` which no longer matches what Plex returns.
        This method mirrors the logic used by the
        ``netplexflix/Missing-Trailer-Downloader-For-Plex`` project by requiring
        both fields to match.
        """
        hits = self.server.library.search(guid=f"tmdb://{tmdb_id}")
        if not hits:
            return False
        item = hits[0]
        try:
            return any(
                getattr(e, "type", None) == "clip"
                and getattr(e, "subtype", None) == "trailer"
                for e in item.extras()
            )
        except Exception as e:  # Plex sometimes 404s on extras()
            log.warning("Plex extras lookup failed for %s: %s", tmdb_id, e)
            return False
