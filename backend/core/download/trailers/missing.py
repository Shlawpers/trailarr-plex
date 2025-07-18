from app_logger import ModuleLogger
from config.settings import app_settings
from core.base.database.manager import trailerprofile
from core.base.database.manager.base import MediaDatabaseManager
from core.base.database.models.media import MediaRead
from core.base.database.models.trailerprofile import TrailerProfileRead
from core.base.utils.filters import matches_filters
from core.download.trailers.batch import batch_download_task
from core.files_handler import FilesHandler
import os
from core.plex_extras import PlexExtras     # path already valid

_PLEX = None
if os.getenv("RESPECT_PLEX_PASS_TRAILERS", "false").lower() == "true":
    _PLEX = PlexExtras(
        url=os.getenv("PLEX_URL", "http://plex:32400"),
        token=os.getenv("PLEX_TOKEN", ""),
    )

logger = ModuleLogger("TrailerDownloadTasks")


def _find_matching_profile_id(
    db_media: MediaRead, trailer_profiles: list[TrailerProfileRead]
) -> int | None:
    """Find a matching profile for a media item and return it's ID."""
    # Sort profiles by priority, higher priority first
    trailer_profiles.sort(key=lambda p: p.priority, reverse=True)
    for profile in trailer_profiles:
        if matches_filters(db_media, profile.customfilter.filters):
            return profile.id
    return None


def _is_valid_media(
    db_media: MediaRead, skipped_titles: dict[str, list[str]]
) -> bool:
    """Check if a media item is valid for downloading."""
    if db_media.folder_path is None:
        skipped_titles["missing_folder_path"].append(db_media.title)
        return False

    if not FilesHandler.check_folder_exists(db_media.folder_path):
        skipped_titles["missing_folder_path"].append(db_media.title)
        return False

    if app_settings.wait_for_media and not FilesHandler.check_media_exists(
        db_media.folder_path
    ):
        skipped_titles["media_not_found"].append(db_media.title)
        return False

    return True


# def _check_file_already_downloaded(
#     media: MediaRead, profile: TrailerProfileRead
# ) -> bool:
#     """Check if the trailer file for the given profile already exists for media."""
#     if not media.folder_path:
#         return False

#     file_name = get_trailer_filename(media, profile, profile.file_format, 1)

#     return FilesHandler.check_file_exists(media.folder_path, file_name)


def _process_media_items(
    db_media_list: list[MediaRead],
    trailer_profiles: list[TrailerProfileRead],
    skipped_titles: dict[str, list[str]],
    profile_to_media_map: dict[int, list[MediaRead]],
) -> int:
    """Process media items and group them by matching profiles."""
    _download_count = 0
    for db_media in db_media_list:
        if not db_media.monitor:
            skipped_titles["not_monitored"].append(db_media.title)
            continue

        # --- Plex-Pass guard ---
        if _PLEX and _PLEX.has_trailer(db_media.txdb_id):
            logger.debug(
                "Plex Pass already provides trailer for '%s' — skipping",
                db_media.title,
            )
            continue
        # -----------------------

        profile_id = _find_matching_profile_id(db_media, trailer_profiles)
        if not profile_id:
            skipped_titles["no_matching_profile"].append(db_media.title)
            continue

        if not _is_valid_media(db_media, skipped_titles):
            continue

        # if _check_file_already_downloaded(
        #     db_media, trailer_profiles[profile_id]
        # ):
        #     skipped_titles["already_downloaded"].append(db_media.title)
        #     continue

        _download_count += 1
        profile_to_media_map[profile_id].append(db_media)
    return _download_count


def _log_skipped_titles(
    skipped_titles: dict[str, list[str]],
    total_media_count: int,
    download_count: int,
) -> None:
    """Log skipped media titles and summary."""
    for skip_reason, skip_titles in skipped_titles.items():
        skip_reason = skip_reason.replace("_", " ")
        logger.debug(f"Skipped {len(skip_titles)} titles - {skip_reason}")
    _skip_count = sum(len(titles) for titles in skipped_titles.values())
    logger.info(
        f"Total {total_media_count} media items checked. "
        f"Skipped: {_skip_count}, Download needed: {download_count}"
    )


async def _download_trailers(
    profile_map: dict[int, TrailerProfileRead],
    profile_to_media_map: dict[int, list[MediaRead]],
    download_count: int,
) -> None:
    """Download trailers for each profile with its media list."""
    _downloading_count = 1
    for profile_id, media_list in profile_to_media_map.items():
        profile = profile_map[profile_id]
        if not media_list:
            continue
        logger.info(
            f"Downloading trailers for {len(media_list)} media items using"
            f" profile: {profile.customfilter.filter_name}"
        )
        await batch_download_task(
            media_list,
            profile,
            downloading_count=_downloading_count,
            download_count=download_count,
        )
        _downloading_count += len(media_list)


async def download_missing_trailers() -> None:
    """Download missing trailers for monitored media items."""
    # Exit if monitoring is disabled
    if not app_settings.monitor_enabled:
        logger.warning("Monitoring is disabled, skipping trailers download")
        return

    db_manager = MediaDatabaseManager()
    db_media_list = db_manager.read_all()
    trailer_profiles = trailerprofile.get_trailerprofiles()

    if not trailer_profiles:
        logger.warning("No TrailerProfiles found, skipping download trailers")
        return
    enabled_profiles: list[TrailerProfileRead] = []
    for profile in trailer_profiles:
        if profile.enabled:
            enabled_profiles.append(profile)
        else:
            logger.debug(
                "Skipping disabled TrailerProfile:"
                f" {profile.customfilter.filter_name}"
            )
    # If no enabled profiles, log a warning and exit.
    if not enabled_profiles:
        logger.warning("No enabled TrailerProfiles found, skipping download")
        return
    # Sort Profiles to the highest priority first
    enabled_profiles.sort(key=lambda p: p.priority, reverse=True)

    # Initialize the dictionary to track skipped titles.
    skipped_titles: dict[str, list[str]] = {
        "no_matching_profile": [],
        "not_monitored": [],
        "missing_folder_path": [],
        "media_not_found": [],
        # "already_downloaded": [],
    }

    # Initialize profile maps for grouping media items.
    profile_map = {profile.id: profile for profile in enabled_profiles}
    profile_to_media_map: dict[int, list[MediaRead]] = {
        profile.id: [] for profile in enabled_profiles
    }

    _download_count = _process_media_items(
        db_media_list, enabled_profiles, skipped_titles, profile_to_media_map
    )

    _log_skipped_titles(skipped_titles, len(db_media_list), _download_count)

    await _download_trailers(
        profile_map, profile_to_media_map, _download_count
    )

    logger.info("Finished downloading missing trailers.")
