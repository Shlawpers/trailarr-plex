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

class DummyLibrary:
    def __init__(self, items):
        self._items = items
    def search(self, **kwargs):
        return self._items

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
    assert plex.has_trailer("42") is True


def test_has_trailer_no_match(monkeypatch):
    server = _make_server([DummyExtra("clip", "featurette"), DummyExtra("trailer", None)])
    monkeypatch.setattr(plex_extras, "PlexServer", lambda url, token: server)
    plex = plex_extras.PlexExtras("http://x", "t")
    assert plex.has_trailer("42") is False

