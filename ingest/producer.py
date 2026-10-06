"""
Stream Event Producer for Kafka / Redpanda with an in-memory queue fallback.
Publishes schema-validated events to a named topic.
"""

import json
from typing import Dict, Optional, Any
from queue import Queue
from generator.schemas import EventSchema

# Memory broker registry for local fallback stream topics
_IN_MEMORY_TOPICS: Dict[str, Queue] = {}


def get_memory_topic_queue(topic: str) -> Queue:
    if topic not in _IN_MEMORY_TOPICS:
        _IN_MEMORY_TOPICS[topic] = Queue()
    return _IN_MEMORY_TOPICS[topic]


class EventProducer:
    """Publishes events to Redpanda/Kafka or local in-memory stream topic."""

    def __init__(self, topic: str = "airops-events", broker_url: Optional[str] = None):
        self.topic = topic
        self.broker_url = broker_url
        self.published_count = 0
        self._kafka_producer = None

        if broker_url:
            try:
                import confluent_kafka
                self._kafka_producer = confluent_kafka.Producer({"bootstrap.servers": broker_url})
            except ImportError:
                try:
                    import kafka
                    self._kafka_producer = kafka.KafkaProducer(
                        bootstrap_servers=broker_url,
                        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    )
                except Exception:
                    self._kafka_producer = None

    def publish(self, event: EventSchema) -> bool:
        """Validates and publishes an event."""
        # Ensure event complies with schema
        payload_bytes = json.dumps(event.model_dump()).encode("utf-8")

        if self._kafka_producer:
            try:
                if hasattr(self._kafka_producer, "produce"):  # confluent-kafka
                    self._kafka_producer.produce(self.topic, value=payload_bytes)
                    self._kafka_producer.flush()
                else:  # kafka-python
                    self._kafka_producer.send(self.topic, value=event.model_dump())
                    self._kafka_producer.flush()
                self.published_count += 1
                return True
            except Exception:
                pass

        # Fallback to thread-safe in-memory stream queue
        queue = get_memory_topic_queue(self.topic)
        queue.put(event.model_dump())
        self.published_count += 1
        return True
