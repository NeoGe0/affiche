import asyncio

from affiche.app.events.event_manager import SSE_QUEUE_MAXSIZE, EventManager

LOGGER_NAME = "affiche.app.events.event_manager"

def _drain(queue: asyncio.Queue) -> list:
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items

def test_subscriber_queue_is_bounded():
    def scenario():
        manager = EventManager()
        queue = manager.subscribe()

        for i in range(SSE_QUEUE_MAXSIZE + 500):
            manager.publish("item_processed", {"item_id": i})

        assert queue.qsize() == SSE_QUEUE_MAXSIZE

    asyncio.run(_as_coro(scenario))

def test_overflow_is_dropped_rather_than_raised():
    def scenario():
        manager = EventManager()
        manager.subscribe()

        for i in range(SSE_QUEUE_MAXSIZE * 2):
            manager.publish("item_processed", {"item_id": i})

    asyncio.run(_as_coro(scenario))

def test_the_oldest_events_are_kept_and_stay_in_order():
    def scenario():
        manager = EventManager()
        queue = manager.subscribe()

        for i in range(SSE_QUEUE_MAXSIZE + 10):
            manager.publish("item_processed", {"item_id": i})

        received = [m["data"]["item_id"] for m in _drain(queue)]
        assert received == list(range(SSE_QUEUE_MAXSIZE))

    asyncio.run(_as_coro(scenario))

def test_a_lagging_subscriber_is_reported_once_not_per_event(caplog):
    def scenario():
        manager = EventManager()
        manager.subscribe()

        with caplog.at_level("WARNING", logger=LOGGER_NAME):
            for i in range(SSE_QUEUE_MAXSIZE + 2000):
                manager.publish("item_processed", {"item_id": i})

        warnings = [r for r in caplog.records if "not keeping up" in r.message]
        assert len(warnings) == 1, "2000 drops must not mean 2000 log lines"

    asyncio.run(_as_coro(scenario))

def test_unsubscribe_reports_the_drop_total(caplog):
    def scenario():
        manager = EventManager()
        queue = manager.subscribe()
        overflow = 250
        for i in range(SSE_QUEUE_MAXSIZE + overflow):
            manager.publish("item_processed", {"item_id": i})

        with caplog.at_level("WARNING", logger=LOGGER_NAME):
            manager.unsubscribe(queue)

        assert f"dropping {overflow} event(s)" in caplog.text or \
               f"after dropping {overflow} event(s)" in caplog.text

    asyncio.run(_as_coro(scenario))

def test_drop_state_does_not_outlive_the_subscriber():
    def scenario():
        manager = EventManager()
        queue = manager.subscribe()
        for i in range(SSE_QUEUE_MAXSIZE + 5):
            manager.publish("item_processed", {"item_id": i})
        manager.unsubscribe(queue)

        assert manager._dropped == {}, "per-subscriber bookkeeping must be cleaned up"

    asyncio.run(_as_coro(scenario))

def test_a_stuck_subscriber_does_not_starve_a_healthy_one():
    def scenario():
        manager = EventManager()
        stuck = manager.subscribe()
        healthy = manager.subscribe()
        received = []

        for i in range(SSE_QUEUE_MAXSIZE + 300):
            manager.publish("item_processed", {"item_id": i})
            received.extend(m["data"]["item_id"] for m in _drain(healthy))

        assert stuck.qsize() == SSE_QUEUE_MAXSIZE
        assert received == list(range(SSE_QUEUE_MAXSIZE + 300)), "healthy client lost events"

    asyncio.run(_as_coro(scenario))

def test_a_subscriber_that_keeps_up_never_drops():
    def scenario():
        manager = EventManager()
        queue = manager.subscribe()

        for i in range(SSE_QUEUE_MAXSIZE * 3):
            manager.publish("item_processed", {"item_id": i})
            queue.get_nowait()

        assert manager._dropped == {}

    asyncio.run(_as_coro(scenario))

async def _as_coro(fn):
    fn()
