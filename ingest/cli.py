"""
CLI interface for event stream replay and stream ingestion testing.
Usage:
  python -m ingest.cli --input data/scenarios/run_001/events.jsonl --speed 0 --topic airops-events
"""

import argparse
import sys
import time
from ingest.replay import EventReplayer
from ingest.producer import EventProducer
from ingest.consumer import EventConsumer


def main():
    parser = argparse.ArgumentParser(description="Replay JSONL event streams to Redpanda/Kafka or stream queue.")
    parser.add_argument("--input", type=str, required=True, help="Path to events.jsonl")
    parser.add_argument("--speed", type=float, default=0.0, help="Replay speed factor (0 = max throughput)")
    parser.add_argument("--topic", type=str, default="airops-events", help="Stream topic name")
    parser.add_argument("--broker", type=str, default=None, help="Kafka/Redpanda bootstrap server (optional)")

    args = parser.parse_args()

    try:
        replayer = EventReplayer(args.input)
        producer = EventProducer(topic=args.topic, broker_url=args.broker)
        consumer = EventConsumer(topic=args.topic, broker_url=args.broker)

        print("==================================================")
        print("AAOP Event Stream Replayer - Ingest Pipeline")
        print("==================================================")
        print(f"Events File:  {args.input}")
        print(f"Total Events: {len(replayer.events)}")
        print(f"Speed Factor: {args.speed}")
        print(f"Topic:        {args.topic}")
        print("==================================================")

        start_time = time.time()
        for event in replayer.replay(speed_factor=args.speed, callback=producer.publish):
            consumed = consumer.poll_event(timeout=0.01)

        # Drain remaining queue events
        while consumer.poll_event(timeout=0.01) is not None:
            pass

        elapsed = time.time() - start_time
        metrics = consumer.metrics.get_lag_metrics(producer)

        print("\nReplay Summary:")
        print(f"Produced Events: {metrics['produced_count']}")
        print(f"Consumed Events: {metrics['consumed_count']}")
        print(f"Invalid Events:  {metrics['invalid_count']}")
        print(f"Consumer Lag:    {metrics['consumer_lag_events']}")
        print(f"Elapsed Time:    {elapsed:.3f}s")
        print(f"Throughput:      {metrics['throughput_eps']} eps")
        print("==================================================")

    except Exception as e:
        print(f"Replay error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
