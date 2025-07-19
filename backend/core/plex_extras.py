from functools import lru_cache
from plexapi.server import PlexServer
from plexapi import exceptions as plex_exc
import logging
import os
import urllib.parse as _u

_PLEX = None
_INIT = False

log = logging.getLogger("trailarr.plex")


class PlexExtras:
    """Tiny wrapper that answers: does Plex already have a trailer?"""

    def __init__(self, url: str, token: str):
        self.server = PlexServer(url, token)

    @lru_cache(maxsize=4096)
    def has_trailer(self, txdb_id: str, is_movie: bool | None = None) -> bool:
        """Return True if Plex shows at least one trailer extra for this ID.

        The Plex API exposes trailers as extras with ``type`` set to ``"clip"``
        and ``subtype`` set to ``"trailer"``.
        Searches Plex using ``tmdb://{id}`` for movies and ``tvdb://{id}`` for
        series. If the first search finds no results, the alternate prefix is
        tried as a fallback.
        """
        prefix = "tmdb" if (is_movie or len(txdb_id) == 6) else "tvdb"
        log.debug(
            "Searching Plex for %s guid %s://%s",
            "movie" if is_movie else "series",
            prefix,
            txdb_id,
        )
        section_name = "Movies" if prefix == "tmdb" else "TV Shows"
        section = self.server.library.section(section_name)
        guid = f"{prefix}://{txdb_id}"
        try:
            item = section.getGuid(guid)
        except plex_exc.NotFound:
            item = None
        if item is None:
            item = next(iter(section.search(guid=_u.quote(guid, safe=""))), None)
        if item is None and prefix in ("tmdb", "tvdb"):
            alt = "tvdb" if prefix == "tmdb" else "tmdb"
            guid_alt = f"{alt}://{txdb_id}"
            try:
                item = section.getGuid(guid_alt)
            except plex_exc.NotFound:
                item = None
            if item is None:
                item = next(
                    iter(section.search(guid=_u.quote(guid_alt, safe=""))), None
                )
        if not item:
            log.debug("No Plex items found for %s", txdb_id)
            return False
        try:
            extras = list(item.extras())
            result = any(
                getattr(e, "type", None) == "clip"
                and getattr(e, "subtype", None) == "trailer"
                for e in extras
            )
            log.debug("Found %d extras for %s -> %s", len(extras), txdb_id, result)
            return result
        except Exception as e:  # Plex sometimes 404s on extras()
            log.warning("Plex extras lookup failed for %s: %s", txdb_id, e)
            return False


def get_plex() -> PlexExtras | None:
    """Lazily create and return a :class:`PlexExtras` instance."""
    global _PLEX, _INIT
    if not _INIT:
        _INIT = True
        if os.getenv("RESPECT_PLEX_PASS_TRAILERS", "false").lower() == "true":
            url = os.getenv("PLEX_URL", "http://plex:32400")
            token = os.getenv("PLEX_TOKEN", "")
            log.info("Respect Plex Pass: enabled. Connecting to Plex at %s", url)
            try:
                _PLEX = PlexExtras(url=url, token=token)
                log.info("Connected to Plex at %s", url)
            except plex_exc.BadRequest as e:
                log.warning("Failed to connect to Plex at %s: %s", url, e)
                _PLEX = None
        else:
            log.info("Respect Plex Pass: disabled")
    return _PLEX
