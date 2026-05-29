"""Minimal async test support for pytest without external plugin."""
from __future__ import annotations

import asyncio
import inspect

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``asyncio`` marker so ``--strict-markers`` works."""
    config.addinivalue_line("markers", "asyncio: mark test as requiring an asyncio event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Run ``async def`` tests using ``asyncio.run`` semantics.

    This mirrors the default behaviour of the ``pytest-asyncio`` plugin for the
    simple cases we have in this project without introducing an extra
    dependency.
    """

    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    marker = pyfuncitem.get_closest_marker("asyncio")
    if marker is None:
        # Let pytest's normal handling complain about missing plugin if a test
        # is a coroutine but not marked appropriately.
        return None

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_func(**pyfuncitem.funcargs))
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    # Returning True tells pytest we executed the test ourselves.
    return True
