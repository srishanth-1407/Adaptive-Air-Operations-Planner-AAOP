"""
State versioning and historical state reconstruction engine.
Allows reconstructing exact past state snapshot at version N from initial state and event log.
"""

from typing import List, Optional
from generator.schemas import EventSchema
from state.models import StateSnapshot, EventLogEntry
from state.transitions import apply_event


class HistoricalStateReconstructor:
    """Manages event log and historical state reconstruction at arbitrary version numbers."""

    def __init__(self, initial_snapshot: StateSnapshot):
        self.initial_snapshot = initial_snapshot
        self.event_log: List[EventLogEntry] = []
        self.current_snapshot = initial_snapshot

    def record_and_apply(self, event: EventSchema) -> StateSnapshot:
        """Applies event, records in log, and increments state version."""
        next_snapshot = apply_event(self.current_snapshot, event)
        self.event_log.append(
            EventLogEntry(
                version=next_snapshot.version.version,
                event=event,
            )
        )
        self.current_snapshot = next_snapshot
        return next_snapshot

    def reconstruct_at_version(self, target_version: int) -> StateSnapshot:
        """
        Reconstructs state snapshot exactly as it existed at version target_version.
        """
        if target_version < 0:
            raise ValueError("target_version cannot be negative")

        if target_version == 0:
            return self.initial_snapshot

        max_version = self.current_snapshot.version.version
        if target_version > max_version:
            raise ValueError(f"Target version {target_version} exceeds current max version {max_version}")

        # Start from initial state S_0 and apply events up to target_version
        state = self.initial_snapshot
        for entry in self.event_log:
            if entry.version <= target_version:
                state = apply_event(state, entry.event)
            else:
                break
        return state
