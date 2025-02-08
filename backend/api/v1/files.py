import os
from fastapi import APIRouter, HTTPException, Response, status, Header

from app_logger import ModuleLogger
from core.base.database.manager.base import MediaDatabaseManager
from core.download import video_analysis
from core.files_handler import FilesHandler, FolderInfo

logger = ModuleLogger("MediaFiles")

files_router = APIRouter(prefix="/files", tags=["Files", "media"])

CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB

UNSAFE_PATHS = [".", "/app", "/bin", "/boot", "/etc", "/lib", "/sbin", "/usr", "/var"]

UNSAFE_PATHS = [".", "/app", "/bin", "/boot", "/etc", "/lib", "/sbin", "/usr", "/var"]


def _is_path_safe(path: str) -> bool:
    """Check if the path is safe.\n
    Args:
        path (str): Path to check.
    Returns:
        bool: True if the path is safe, False otherwise."""
    norm_path = os.path.normpath(path)
    abs_path = os.path.abspath(norm_path)
    # Check if path is in unsafe paths
    for unsafe_path in UNSAFE_PATHS:
        if abs_path.startswith(unsafe_path):
            return False
    # Check if path is atleast 3 levels deep
    if abs_path.count("/") < 3:
        return False
    return True


@files_router.get("/files")
async def get_files(path: str) -> FolderInfo | None:
    """Get files in a directory.\n
    Args:
        path (str): Path to the directory.
    Returns:
        FolderInfo|None: Folder information or None if folder doesn't exist. \n
    Raises:
        HTTPException (404): If the folder is not found."""
    try:
        files_handler = FilesHandler()
        return await files_handler.get_folder_files(path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@files_router.get("/video")
async def video_endpoint(file_path: str, range: str = Header(None)):
    """Stream video files.\n
    Args:
        file_path (str): Path to the video file.
        range (str, optional): Range of bytes to stream. Defaults to Header(None). \n
    Raises:
        HTTPException (400): If the file path is invalid.
        HTTPException (404): If the file is not found.
        HTTPException (400): If the file is not a video file. \n
    Returns:
        Response: Video stream response."""
    if not _is_path_safe(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT, detail="File not found."
        )
    _VALID_VIDEOS = [".mkv", ".mp4", ".avi", ".webm"]
    if not file_path.endswith(tuple(_VALID_VIDEOS)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a video file."
        )
    start, end = range.replace("bytes=", "").split("-")
    filesize = os.path.getsize(file_path)
    start = int(start)
    end = int(end) if end else start + CHUNK_SIZE
    if end > filesize:
        end = filesize
    # logger.info(f"Range: {start}-{end}")
    with open(file_path, "rb") as video:
        video.seek(start)
        data = video.read(end - start)
        headers = {
            "Content-Range": f"bytes {str(start)}-{str(end - 1)}/{filesize}",
            "Accept-Ranges": "bytes",
        }
        return Response(data, status_code=206, headers=headers, media_type="video/mp4")


@files_router.get(
    "/read",
    status_code=status.HTTP_200_OK,
    description="Read the contents of a file.",
)
async def read_file(file_path: str) -> str:
    """Read the contents of a file.\n
    Args:
        file_path (str): Path of the file to read. \n
    Raises:
        HTTPException (400): If the file path is invalid. \n
    Returns:
        str: Contents of the file."""
    if not _is_path_safe(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    file_ext = os.path.splitext(file_path)[1]
    VALID_FILE_TYPES = [".txt", ".srt", ".log", ".json", ".py", ".sh"]
    if file_ext not in VALID_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type."
        )
    with open(file_path, "r") as file:
        return file.read().strip()


@files_router.get(
    "/video_info",
    status_code=status.HTTP_200_OK,
    description="Get information about the video file.",
)
def get_video_info(file_path: str) -> video_analysis.VideoInfo | None:
    """Get information about the video file.\n
    Args:
        file_path (str): Path of the video file. \n
    Raises:
        HTTPException (400): If the file path is invalid. \n
    Returns:
        VideoInfo|None: VideoInfo object containing information about the video file.
    """
    if not _is_path_safe(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    return video_analysis.get_media_info(file_path)


# @files_router.post(
#     "/remove_tracks",
#     status_code=status.HTTP_200_OK,
#     description="Remove unwanted tracks from the given video file.",
# )
# def remove_tracks(file_path: str) -> str:
#     """Remove unwanted tracks from the given video file.\n
#     Args:
#         file_path (str): Path of the video file.
#     Returns:
#         str: Message indicating the status of the operation."""
#     try:
#         res = mkv_edit.remove_unwanted_tracks(file_path)
#     except Exception as e:
#         return str(e)
#     return res


@files_router.post(
    "/rename",
    status_code=status.HTTP_200_OK,
    description="Rename a file or folder.",
)
async def rename_file_fol(old_path: str, new_path: str) -> bool:
    """Rename a file or folder.\n
    Args:
        old_path (str): Path of the file/folder to rename.
        new_path (str): New path of the file/folder. \n
    Raises:
        HTTPException (400): If the file path is invalid. \n
    Returns:
        bool: True if the file/folder was renamed successfully, False otherwise."""
    if not _is_path_safe(old_path) or not _is_path_safe(new_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    return await FilesHandler.rename_file_fol(old_path, new_path)


@files_router.delete(
    "/delete",
    status_code=status.HTTP_200_OK,
    description="Delete a file/folder from the filesystem.",
)
async def delete_file_fol(path: str, media_id: int = -1) -> bool:
    """Delete a file/folder from the filesystem.\n
    Args:
        path (str): Path to the file/folder to delete.
        media_id (int, optional): Media ID to delete. Defaults to -1. \n
    Raises:
        HTTPException (400): If the file path is invalid. \n
    Returns:
        bool: True if the file/folder was deleted successfully, False otherwise."""
    if not _is_path_safe(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    deleted_status = await FilesHandler.delete_file_fol(path)
    if media_id != -1 and deleted_status:
        # Media id is provided, if file is trailer, update db
        if "trailer" in path:
            logger.info(f"Updating trailer status for media_id: {media_id}")
            db = MediaDatabaseManager()
            db.update_trailer_exists(media_id, False)
    return deleted_status
