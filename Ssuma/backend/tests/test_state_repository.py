import pytest
from core.state_repository import StateRepository


@pytest.fixture(autouse=True)
def clean_state():
    StateRepository._cache = {}
    StateRepository._initialized = False
    StateRepository._access_order = {}
    yield


def test_save_and_load():
    StateRepository.initialize(db_path=":memory:")
    StateRepository.save("test_service", "proj-1", {"key": "value", "count": 42})
    data = StateRepository.load("test_service", "proj-1")
    assert data is not None
    assert data["key"] == "value"
    assert data["count"] == 42


def test_load_nonexistent():
    StateRepository.initialize(db_path=":memory:")
    data = StateRepository.load("nonexistent", "proj-x")
    assert data is None


def test_overwrite():
    StateRepository.initialize(db_path=":memory:")
    StateRepository.save("svc", "p1", {"version": 1})
    StateRepository.save("svc", "p1", {"version": 2})
    data = StateRepository.load("svc", "p1")
    assert data["version"] == 2


def test_delete():
    StateRepository.initialize(db_path=":memory:")
    StateRepository.save("svc", "p1", {"data": "test"})
    StateRepository.delete("svc", "p1")
    data = StateRepository.load("svc", "p1")
    assert data is None


def test_delete_nonexistent():
    StateRepository.initialize(db_path=":memory:")
    StateRepository.delete("nonexistent", "proj-x")


def test_cache_hit():
    StateRepository.initialize(db_path=":memory:")
    StateRepository._cache["svc"] = {"p1": {"from_cache": True}}
    StateRepository._initialized = True
    data = StateRepository.load("svc", "p1")
    assert data["from_cache"] is True


def test_complex_data_types():
    StateRepository.initialize(db_path=":memory:")
    data = {
        "string": "hello",
        "number": 42,
        "list": [1, 2, 3],
        "nested": {"a": {"b": "deep"}},
        "bool": True,
    }
    StateRepository.save("svc", "p1", data)
    loaded = StateRepository.load("svc", "p1")
    assert loaded["string"] == "hello"
    assert loaded["list"] == [1, 2, 3]
    assert loaded["nested"]["a"]["b"] == "deep"
