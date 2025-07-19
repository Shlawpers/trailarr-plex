import backend.core.plex_extras as plex_extras


class DummyExtra:
    def __init__(self, type=None, subtype=None):
        self.type = type
        self.subtype = subtype


class DummyItem:
    def __init__(self, extras):
        self._extras = extras

    def extras(self):
        return self._extras


class DummySection:
    def __init__(self, items):
        self._items = items

    def getGuid(self, guid):
        if self._items:
            return self._items[0]
        raise plex_extras.plex_exc.NotFound

    def search(self, **kwargs):
        return self._items


class DummyLibrary:
    def __init__(self, items):
        self._section = DummySection(items)

    def section(self, name):
        return self._section


class DummyServer:
    def __init__(self, items):
        self.library = DummyLibrary(items)


def _make_server(extras_list):
    item = DummyItem(extras_list)
    return DummyServer([item])


def test_has_trailer_matches(monkeypatch):
    server = _make_server([DummyExtra("clip", "trailer")])
    monkeypatch.setattr(plex_extras, "PlexServer", lambda url, token: server)
    plex = plex_extras.PlexExtras("http://x", "t")
    assert plex.has_trailer("42", is_movie=True) is True


def test_has_trailer_no_match(monkeypatch):
    server = _make_server(
        [DummyExtra("clip", "featurette"), DummyExtra("trailer", None)]
    )
    monkeypatch.setattr(plex_extras, "PlexServer", lambda url, token: server)
    plex = plex_extras.PlexExtras("http://x", "t")
    assert plex.has_trailer("42", is_movie=True) is False


def test_has_trailer_tvdb(monkeypatch):
    server = _make_server([DummyExtra("clip", "trailer")])
    monkeypatch.setattr(plex_extras, "PlexServer", lambda url, token: server)
    plex = plex_extras.PlexExtras("http://x", "t")
    assert plex.has_trailer("12345", is_movie=False) is True


def test_has_trailer_not_found(monkeypatch):
    server = _make_server([])
    monkeypatch.setattr(plex_extras, "PlexServer", lambda url, token: server)
    plex = plex_extras.PlexExtras("http://x", "t")
    assert plex.has_trailer("42", is_movie=True) is False
