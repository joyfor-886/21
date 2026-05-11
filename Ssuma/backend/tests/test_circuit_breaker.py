import time
import pytest
from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_initial_state():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    assert cb.state == "closed"
    assert cb._failure_count == 0


@pytest.mark.asyncio
async def test_successful_call():
    cb = CircuitBreaker(failure_threshold=3)

    async def success():
        return "ok"

    result = await cb.call(success)
    assert result == "ok"
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    async def fail():
        raise ValueError("test error")

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(fail)

    assert cb.state == "open"
    assert cb._failure_count == 3


@pytest.mark.asyncio
async def test_rejects_when_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    async def fail():
        raise RuntimeError("fail")

    # Trip the breaker
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(RuntimeError):
        await cb.call(fail)

    assert cb.state == "open"

    async def success():
        return "ok"

    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(success)


@pytest.mark.asyncio
async def test_half_open_transition():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb._state = "open"
    cb._failure_count = 2
    cb._last_failure_time = 0
    assert cb.state == "half_open"


@pytest.mark.asyncio
async def test_recovers_from_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    async def fail():
        raise RuntimeError("fail")

    # Trip the breaker
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(RuntimeError):
        await cb.call(fail)

    assert cb.state == "open"
    cb._last_failure_time = 0
    assert cb.state == "half_open"

    async def succeed():
        return "recovered"

    result = await cb.call(succeed)
    assert result == "recovered"
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    async def fail():
        raise RuntimeError("fail")

    # Trip and go half-open
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    cb._last_failure_time = 0
    assert cb.state == "half_open"

    # Fail again
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    assert cb.state == "open"


@pytest.mark.asyncio
async def test_reset():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    cb._failure_count = 5
    cb._state = "open"
    cb.reset()
    assert cb.state == "closed"
    assert cb._failure_count == 0
    assert cb._half_open_calls == 0


@pytest.mark.asyncio
async def test_stats():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    stats = cb.stats()
    assert stats["state"] == "closed"
    assert stats["failure_threshold"] == 3
    assert stats["recovery_timeout"] == 30
    assert "failure_count" in stats
