from typing import Annotated

from fastapi import Depends, FastAPI, Query, Security
from fastapi.dependencies.models import Dependant, _is_subtree_cacheable
from fastapi.testclient import TestClient
from pydantic import AfterValidator

app = FastAPI()

counter_holder = {"counter": 0}


async def dep_counter():
    counter_holder["counter"] += 1
    return counter_holder["counter"]


async def super_dep(count: int = Depends(dep_counter)):
    return count


@app.get("/counter/")
async def get_counter(count: int = Depends(dep_counter)):
    return {"counter": count}


@app.get("/sub-counter/")
async def get_sub_counter(
    subcount: int = Depends(super_dep), count: int = Depends(dep_counter)
):
    return {"counter": count, "subcounter": subcount}


@app.get("/sub-counter-no-cache/")
async def get_sub_counter_no_cache(
    subcount: int = Depends(super_dep),
    count: int = Depends(dep_counter, use_cache=False),
):
    return {"counter": count, "subcounter": subcount}


@app.get("/scope-counter")
async def get_scope_counter(
    count: int = Security(dep_counter),
    scope_count_1: int = Security(dep_counter, scopes=["scope"]),
    scope_count_2: int = Security(dep_counter, scopes=["scope"]),
):
    return {
        "counter": count,
        "scope_counter_1": scope_count_1,
        "scope_counter_2": scope_count_2,
    }


client = TestClient(app)


def test_normal_counter():
    counter_holder["counter"] = 0
    response = client.get("/counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 1}
    response = client.get("/counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 2}


def test_sub_counter():
    counter_holder["counter"] = 0
    response = client.get("/sub-counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 1, "subcounter": 1}
    response = client.get("/sub-counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 2, "subcounter": 2}


def test_sub_counter_no_cache():
    counter_holder["counter"] = 0
    response = client.get("/sub-counter-no-cache/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 2, "subcounter": 1}
    response = client.get("/sub-counter-no-cache/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 4, "subcounter": 3}


def test_security_cache():
    counter_holder["counter"] = 0
    response = client.get("/scope-counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 1, "scope_counter_1": 2, "scope_counter_2": 2}
    response = client.get("/scope-counter/")
    assert response.status_code == 200, response.text
    assert response.json() == {"counter": 3, "scope_counter_1": 4, "scope_counter_2": 4}


def test_cached_dependency_subtree_not_resolved_again():
    local_app = FastAPI()
    validator_calls = 0

    def count_validation(v: int) -> int:
        nonlocal validator_calls
        validator_calls += 1
        return v

    async def cached_leaf(
        q: Annotated[int, Query(), AfterValidator(count_validation)] = 1,
    ) -> int:
        return q + 1

    async def cached_middle(val: int = Depends(cached_leaf)) -> int:
        return val

    async def branch_a(mid: int = Depends(cached_middle)) -> int:
        return mid

    async def branch_b(mid: int = Depends(cached_middle)) -> int:
        return mid

    @local_app.get("/diamond")
    async def diamond_endpoint(
        a: int = Depends(branch_a),
        b: int = Depends(branch_b),
    ):
        return {"a": a, "b": b}

    local_client = TestClient(local_app)
    response = local_client.get("/diamond?q=5")
    assert response.status_code == 200
    assert response.json() == {"a": 6, "b": 6}
    assert validator_calls == 1


def test_cached_dependency_with_uncached_subdependency_executes_uncached_leaf():
    local_app = FastAPI()
    uncached_leaf_calls = 0
    cached_leaf_calls = 0
    middle_calls = 0

    async def uncached_leaf() -> int:
        nonlocal uncached_leaf_calls
        uncached_leaf_calls += 1
        return uncached_leaf_calls

    async def cached_leaf() -> int:
        nonlocal cached_leaf_calls
        cached_leaf_calls += 1
        return cached_leaf_calls

    async def cached_middle(
        uncached_val: int = Depends(uncached_leaf, use_cache=False),
        cached_val: int = Depends(cached_leaf),
    ) -> int:
        nonlocal middle_calls
        middle_calls += 1
        return uncached_val + cached_val

    async def branch_a(mid: int = Depends(cached_middle)) -> int:
        return mid

    async def branch_b(mid: int = Depends(cached_middle)) -> int:
        return mid

    @local_app.get("/diamond-uncached-leaf")
    async def diamond_endpoint(
        a: int = Depends(branch_a),
        b: int = Depends(branch_b),
    ):
        return {"a": a, "b": b}

    local_client = TestClient(local_app)
    response = local_client.get("/diamond-uncached-leaf")
    assert response.status_code == 200
    assert response.json() == {"a": 2, "b": 2}
    assert middle_calls == 1
    assert cached_leaf_calls == 1
    assert uncached_leaf_calls == 2


def test_cached_dependency_with_overridden_uncached_subdependency():
    local_app = FastAPI()
    uncached_override_calls = 0

    async def original_leaf() -> int:
        return 1  # pragma: no cover

    async def cached_middle(val: int = Depends(original_leaf)) -> int:
        return val

    async def branch_a(mid: int = Depends(cached_middle)) -> int:
        return mid

    async def branch_b(mid: int = Depends(cached_middle)) -> int:
        return mid

    @local_app.get("/diamond-overridden-leaf")
    async def diamond_endpoint(
        a: int = Depends(branch_a),
        b: int = Depends(branch_b),
    ):
        return {"a": a, "b": b}

    async def uncached_sub() -> int:
        nonlocal uncached_override_calls
        uncached_override_calls += 1
        return uncached_override_calls

    async def override_leaf(
        val: int = Depends(uncached_sub, use_cache=False),
    ) -> int:
        return val

    local_app.dependency_overrides[original_leaf] = override_leaf

    local_client = TestClient(local_app)
    response = local_client.get("/diamond-overridden-leaf")
    assert response.status_code == 200
    assert response.json() == {"a": 1, "b": 1}
    assert uncached_override_calls == 2


def test_is_subtree_cacheable_direct():
    leaf = Dependant(call=lambda: 1, use_cache=True)
    root = Dependant(call=None, dependencies=[leaf], use_cache=True)
    assert _is_subtree_cacheable(dependant=root) is True
