"""
Event Stream Replay Engine.
Supports JSONL event stream loading and replay with timing controls:
- 1x real-time mode
- Accelerated mode (e.g. 10x, 100x)
- Maximum throughput mode (0 delay)
"""

import json
import time
from pathlib import Path
from typing import Callable, Generator, List, Optional
from generator.schemas import EventSchema


class EventReplayer:
    """Reads JSONL event stream and replays events with speed control."""

    def __init__(self, events_jsonl_path: str):
        self.path = Path(events_jsonl_path)
        if not self.path.is_file():
            raise FileNotFoundError(f"Event stream file not found: {events_jsonl_path}")
        self.events: List[EventSchema] = self._load_events()

    def _load_events(self) -> List[EventSchema]:
        events = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = EventSchema.model_validate(data)
                    events.append(event)
                except Exception as e:
                    raise ValueError(f"Invalid event schema at line {line_idx}: {e}")
        # Ensure strict chronological ordering
        events.sort(key=lambda e: e.timestamp)
        return events

    def replay(
        self,
        speed_factor: float = 1.0,
        max_events: Optional[int] = None,
        callback: Optional[Callable[[EventSchema], None]] = None,
    ) -> Generator[EventSchema, None, None]:
        """
        Replays events yielding one by one or invoking callback.
        - speed_factor == 1.0: 1x real time (simulated hour -> 1 second or 1:1 ratio)
        - speed_factor > 1.0: Accelerated replay
        - speed_factor == 0 or inf: Maximum throughput (no sleep)
        """
        prev_sim_time: Optional[float] = None
        count = 0

        for event in self.events:
            if max_events is not None and count >= max_events:
                break

            if prev_sim_time is not None and speed_factor > 0 and speed_factor != float("inf"):
                time_delta = event.timestamp - prev_sim_time
                if time_delta > 0:
                    sleep_sec = time_delta / speed_factor
                    # Cap single sleep to prevent hangs in tests
                    time.sleep(min(sleep_sec, 2.0))

            prev_sim_time = event.timestamp
            count += 1

            if callback:
                callback(event)

            yield event
