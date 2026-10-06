"""
Stream Event Consumer for Kafka / Redpanda with schema validation and consumer lag metrics.
"""

import json
import time
from typing import Dict, Generator, Optional, Any
from pydantic import ValidationError

from generator.schemas import EventSchema
from ingest.producer import get_memory_topic_queue, EventProducer


class ConsumerMetrics:
    """Tracks stream consumer lag and performance metrics."""

    def __init__(self):
        self.consumed_count: int = 0
        self.invalid_count: int = 0
        self.latest_event_timestamp: Optional[float] = None
        self.start_time: float = time.time()

    def record_success(self, event: EventSchema):
        self.consumed_count += 1
        self.latest_event_timestamp = event.timestamp

    def record_failure(self):
        self.invalid_count += 1

    @property
    def elapsed_seconds(self) -> float:
        return max(0.001, time.time() - self.start_time)

    @property
    def throughput_eps(self) -> float:
        return round(self.consumed_count / self.elapsed_seconds, 2)

    def get_lag_metrics(self, producer: Optional[EventProducer] = None) -> Dict[str, Any]:
        produced_count = producer.published_count if producer else self.consumed_count
        lag = max(0, produced_count - self.consumed_count)
        return {
            "produced_count": produced_count,
            "consumed_count": self.consumed_count,
            "invalid_count": self.invalid_count,
            "consumer_lag_events": lag,
            "latest_event_timestamp": self.latest_event_timestamp,
            "throughput_eps": self.throughput_eps,
        }


class EventConsumer:
    """Consumes and validates event stream from Kafka/Redpanda or in-memory fallback queue."""

    def __init__(self, topic: str = "airops-events", broker_url: Optional[str] = None):
        self.topic = topic
        self.broker_url = broker_url
        self.metrics = ConsumerMetrics()
        self._kafka_consumer = None

        if broker_url:
            try:
                import confluent_kafka
                self._kafka_consumer = confluent_kafka.Consumer(
                    {
                        "bootstrap.servers": broker_url,
                        "group.id": "airops-group",
                        "auto.offset.reset": "earliest",
                    }
                )
                self._kafka_consumer.subscribe([self.topic])
            except Exception:
                self._kafka_consumer = None

    def poll_event(self, timeout: float = 0.1) -> Optional[EventSchema]:
        """Polls next event from queue/stream. Returns validated EventSchema or None."""
        raw_data = None

        if self._kafka_consumer:
            try:
                msg = self._kafka_consumer.poll(timeout)
                if msg is not None and not msg.error():
                    raw_data = json.loads(msg.value().decode("utf-8"))
            except Exception:
                raw_data = None

        if raw_data is None:
            queue = get_memory_topic_queue(self.topic)
            if not queue.empty():
                raw_data = queue.get_nowait()

        if raw_data is None:
            return None

        try:
            event = EventSchema.model_validate(raw_data)
            self.metrics.record_success(event)
            return event
        except (ValidationError, Exception):
            self.metrics.record_failure()
            return None

    def consume_stream(
        self, timeout_seconds: float = 1.0
    ) -> Generator[EventSchema, None, None]:
        """Continuously yields validated events from the stream until timeout idle."""
        last_item_time = time.time()
        while True:
            event = self.poll_event(timeout=0.05)
            if event is not None:
                last_item_time = time.time()
                yield event
            else:
                if time.time() - last_item_time > timeout_seconds:
                    break
                time.sleep(0.01)
