"""
Unit and integration tests for producer, consumer, lag metrics, and schema validation error handling.
"""

import pytest
from generator.schemas import EventSchema
from ingest.producer import EventProducer, get_memory_topic_queue
from ingest.consumer import EventConsumer


def test_producer_consumer_stream_equivalence():
    topic = "test-stream-topic-1"
    producer = EventProducer(topic=topic)
    consumer = EventConsumer(topic=topic)

    event1 = EventSchema(
        event_id="E-00001",
        timestamp=1.5,
        kind="ASSET_UNAVAILABLE",
        schema_version=1,
        payload={"asset_id": "A-0001", "reason": "test"},
    )
    event2 = EventSchema(
        event_id="E-00002",
        timestamp=2.0,
        kind="ASSET_AVAILABLE",
        schema_version=1,
        payload={"asset_id": "A-0001"},
    )

    producer.publish(event1)
    producer.publish(event2)

    consumed_1 = consumer.poll_event(timeout=0.1)
    consumed_2 = consumer.poll_event(timeout=0.1)

    assert consumed_1 is not None
    assert consumed_1.event_id == "E-00001"
    assert consumed_2 is not None
    assert consumed_2.event_id == "E-00002"

    # Lag metrics
    lag = consumer.metrics.get_lag_metrics(producer)
    assert lag["produced_count"] == 2
    assert lag["consumed_count"] == 2
    assert lag["consumer_lag_events"] == 0


def test_consumer_schema_validation_error_handling():
    topic = "test-corrupted-topic"
    queue = get_memory_topic_queue(topic)
    consumer = EventConsumer(topic=topic)

    # Push invalid/corrupted payload missing required fields
    queue.put({"bad_field": "invalid"})

    consumed = consumer.poll_event(timeout=0.1)
    assert consumed is None
    assert consumer.metrics.invalid_count == 1
