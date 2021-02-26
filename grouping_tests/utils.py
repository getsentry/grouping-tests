from pathlib import Path
import textwrap


def event_path(event_id: str, extension: str = "", prefix_length=2, num_levels=2) -> Path:
    """ Spread out files by chopping up the event ID """
    id_parts = textwrap.wrap(event_id, prefix_length)
    target_dir = Path().joinpath(*id_parts[:num_levels])

    return target_dir / f"event_{event_id}{extension}"