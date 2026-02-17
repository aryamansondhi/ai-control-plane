from prometheus_client import Counter

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