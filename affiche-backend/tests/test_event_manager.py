import asyncio
import threading
from unittest.mock import MagicMock

from affiche.app.events.event_manager import EventManager

def test_publish_marshals_via_loop_call_soon_threadsafe():
    em = EventManager()
    q1, q2 = em.subscribe(), em.subscribe()

    loop = MagicMock()
    loop.is_running.return_value = True
    em.set_loop(loop)

    em.publish("task_status", {"x": 1})

    assert loop.call_soon_threadsafe.call_count == 2
    scheduled_queues = {call.args[1] for call in loop.call_soon_threadsafe.call_args_list}
    assert scheduled_queues == {q1, q2}
    message = loop.call_soon_threadsafe.call_args_list[0].args[2]
    assert message == {"type": "task_status", "data": {"x": 1}}
    assert q1.empty() and q2.empty()

def test_publish_without_loop_falls_back_to_direct_put():
    em = EventManager()
    q = em.subscribe()

    em.publish("item_processed", {"library_id": 1, "item_id": 2})

    assert q.get_nowait() == {"type": "item_processed", "data": {"library_id": 1, "item_id": 2}}

def test_no_subscribers_is_noop():
    em = EventManager()
    em.set_loop(MagicMock())
    em.publish("task_status", {"x": 1})

def test_concurrent_subscribe_during_publish_does_not_raise():
    em = EventManager()
    for _ in range(50):
        em.subscribe()

    stop = threading.Event()

    def churn():
        while not stop.is_set():
            q = em.subscribe()
            em.unsubscribe(q)

    t = threading.Thread(target=churn)
    t.start()
    try:
        for _ in range(200):
            em.publish("task_status", {"n": 1})
    finally:
        stop.set()
        t.join()
