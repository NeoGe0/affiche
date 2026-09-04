import importlib
import inspect

ROUTER_MODULES = [
    "config", "events", "library", "media_server",
    "service", "settings", "tasks", "poster",
]

ASYNC_ALLOWLIST = {"event_stream"}

def _all_routes():
    for name in ROUTER_MODULES:
        module = importlib.import_module(f"affiche.api.routers.{name}")
        for route in module.router.routes:
            yield name, route.path, route.endpoint

def test_only_sse_endpoint_is_async():
    offenders = [
        f"{mod}:{endpoint.__name__} ({path})"
        for mod, path, endpoint in _all_routes()
        if inspect.iscoroutinefunction(endpoint) and endpoint.__name__ not in ASYNC_ALLOWLIST
    ]
    assert offenders == [], (
        "These handlers are async def but should be plain def (blocking I/O would freeze "
        f"the event loop): {offenders}"
    )

def test_sse_endpoint_stays_async():
    async_names = {
        endpoint.__name__
        for _, _, endpoint in _all_routes()
        if inspect.iscoroutinefunction(endpoint)
    }
    assert async_names == ASYNC_ALLOWLIST, (
        f"Expected only {ASYNC_ALLOWLIST} to be async; got {async_names}"
    )

def test_guard_sees_a_meaningful_number_of_routes():
    routes = list(_all_routes())
    assert len(routes) > 30
