from datetime import datetime, timedelta
from sqlmodel import col, desc, select
from config.logs.db_utils import get_async_logs_session
from config.logs.model import AppLogRecord, LOG_LEVELS, LogLevel
from config.settings import app_settings


async def get_all_logs(
    level: LogLevel | None = None, offset: int = 0, limit: int = 1000
) -> list[AppLogRecord]:
    """Retrieve all logs from the database."""

    if level is None:
        level = LogLevel[app_settings.log_level]
    async with get_async_logs_session() as session:
        stmt = select(AppLogRecord)
        # Get log levels greater than or equal to the specified level
        _given_val = LOG_LEVELS.get(level.value.upper(), 20)
        _levels_to_get = [
            _level
            for _level, _value in LOG_LEVELS.items()
            if _value >= _given_val
        ]
        stmt = stmt.where(col(AppLogRecord.level).in_(_levels_to_get))
        stmt = (
            stmt.offset(offset)
            .limit(limit)
            .order_by(desc(AppLogRecord.created))
        )
        logs = await session.exec(stmt)
        return list(logs)


async def delete_old_logs(days: int = 30) -> int:
    """Delete logs older than the specified number of days."""
    date_threshold = datetime.now() - timedelta(days=days)
    async with get_async_logs_session() as session:
        stmt = select(AppLogRecord).where(
            col(AppLogRecord.created) < date_threshold
        )
        logs_to_delete = await session.exec(stmt)
        logs_to_delete = logs_to_delete.all()
        count = len(logs_to_delete)
        if logs_to_delete:
            for log in logs_to_delete:
                await session.delete(log)
            await session.commit()
        return count
