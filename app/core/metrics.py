from prometheus_client import Counter, Histogram

publish_latency_seconds = Histogram(
    "publish_latency_seconds",
    "Time taken to publish an event"
)

events_published = Counter(
    "events_published_total",
    "Total successfully published events"
)

events_failed = Counter(
    "events_failed_total",
    "Total failed publish attempts"
)

events_dead_lettered = Counter(
    "events_dead_lettered_total",
    "Total events dead-lettered"
)