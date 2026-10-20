"""Append feedback provenance locally; never stores API credentials."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .behavior import validate_behavior


def record_history(path, instruction, generated, feedback=None, updated=None, *, executed=False,
                   backend='offline', adapter='mock'):
    event = {'timestamp': datetime.now(timezone.utc).isoformat(),
             'instruction': instruction, 'generated_behavior': validate_behavior(generated),
             'human_feedback': feedback,
             'updated_behavior': validate_behavior(updated) if updated is not None else None,
             'executed': executed, 'backend': backend, 'adapter': adapter}
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
