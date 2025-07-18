from types import SimpleNamespace
import backend.core.tasks.download_trailers as dl

class DummyPlex:
    def __init__(self, result: bool):
        self.result = result
    def has_trailer(self, tmdb_id: str) -> bool:
        return self.result


def _setup_common(monkeypatch, plex_result=False):
    media = SimpleNamespace(
        id=1,
        title="Dummy",
        is_movie=True,
        folder_path="/tmp",
        txdb_id="123",
        youtube_trailer_id=None,
    )
    profile = SimpleNamespace(always_search=False)
    monkeypatch.setattr(dl.MediaDatabaseManager, "read", lambda self, _: media)
    monkeypatch.setattr(dl.trailerprofile, "get_trailerprofile", lambda _: profile)
    monkeypatch.setattr(dl.FilesHandler, "check_folder_exists", lambda _: True)
    calls = []
    monkeypatch.setattr(dl.scheduler, "add_job", lambda *a, **k: calls.append((a,k)))
    monkeypatch.setattr(dl, "_PLEX", DummyPlex(plex_result))
    return media, profile, calls


def test_skip_when_plex_has_trailer(monkeypatch):
    _, _, calls = _setup_common(monkeypatch, plex_result=True)
    msg = dl.download_trailer_by_id(1, 1)
    assert not calls
    assert "Plex Pass already provides trailer" in msg


def test_schedule_when_no_plex_trailer(monkeypatch):
    _, _, calls = _setup_common(monkeypatch, plex_result=False)
    msg = dl.download_trailer_by_id(1, 1)
    assert calls
    assert "Trailer download started" in msg

