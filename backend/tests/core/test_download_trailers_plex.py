from types import SimpleNamespace
import asyncio
import backend.core.tasks.download_trailers as dl
import backend.core.download.trailer as trailer

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


def test_direct_download_respects_plex_pass(monkeypatch):
    media = SimpleNamespace(
        id=1,
        title="Dummy",
        is_movie=True,
        folder_path="/tmp",
        txdb_id="321",
        youtube_trailer_id=None,
        trailer_exists=False,
    )
    profile = SimpleNamespace(
        always_search=False,
        file_format="mp4",
        remove_silence=False,
    )

    monkeypatch.setattr(trailer, "_PLEX", DummyPlex(True))

    def fail(*args, **kwargs):
        raise AssertionError("should not download")

    monkeypatch.setattr(trailer.trailer_search, "get_video_id", fail)
    monkeypatch.setattr(trailer, "__update_media_status", lambda *a, **k: None)
    monkeypatch.setattr(trailer.trailer_file, "move_trailer_to_folder", lambda *a, **k: None)
    monkeypatch.setattr(trailer.trailer_file, "verify_download", lambda *a, **k: True)
    monkeypatch.setattr(trailer, "download_video", lambda *a, **k: "f.mp4")
    monkeypatch.setattr(trailer.video_analysis, "remove_silence_at_end", lambda x: x)

    result = asyncio.run(trailer.download_trailer(media, profile))
    assert result is True

