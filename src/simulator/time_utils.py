from __future__ import annotations

from datetime import datetime


TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M",
]

CANONICAL_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_timestamp(value: datetime) -> str:
    """
    Convert a datetime object into the simulator's
    canonical output format.
    """
    return value.strftime(CANONICAL_TIMESTAMP_FORMAT)


def parse_timestamp(value: str) -> datetime:
    """
    Parse any timestamp format intentionally supported
    by the simulator's source data.
    """
    for timestamp_format in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(
                value,
                timestamp_format,
            )
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported timestamp format: {value!r}"
    )