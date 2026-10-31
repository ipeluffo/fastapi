import pytest
from fastapi import APIRouter, Depends, FastAPI, Security
from fastapi.dependencies import utils as dependency_utils
from fastapi.security import SecurityScopes
from fastapi.testclient import TestClient

app = FastAPI()

router = APIRouter()


async def common_parameters(q: str, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


@app.get("/main-depends/")
async def main_depends(commons: dict = Depends(common_parameters)):
    return {"in": "main-depends", "params": commons}


@app.get("/decorator-depends/", dependencies=[Depends(common_parameters)])
async def decorator_depends():
    return {"in": "decorator-depends"}


@router.get("/router-depends/")
async def router_depends(commons: dict = Depends(common_parameters)):
    return {"in": "router-depends", "params": commons}


@router.get("/router-decorator-depends/", dependencies=[Depends(common_parameters)])
async def router_decorator_depends():
    return {"in": "router-decorator-depends"}


app.include_router(router)

client = TestClient(app)


async def overrider_dependency_simple(q: str | None = None):
    return {"q": q, "skip": 5, "limit": 10}


async def overrider_sub_dependency(k: str):
    return {"k": k}


async def overrider_dependency_with_sub(msg: dict = Depends(overrider_sub_dependency)):
    return msg


def test_main_depends():
    response = client.get("/main-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "q"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_main_depends_q_foo():
    response = client.get("/main-depends/?q=foo")
    assert response.status_code == 200
    assert response.json() == {
        "in": "main-depends",
        "params": {"q": "foo", "skip": 0, "limit": 100},
    }


def test_main_depends_q_foo_skip_100_limit_200():
    response = client.get("/main-depends/?q=foo&skip=100&limit=200")
    assert response.status_code == 200
    assert response.json() == {
        "in": "main-depends",
        "params": {"q": "foo", "skip": 100, "limit": 200},
    }


def test_decorator_depends():
    response = client.get("/decorator-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "q"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_decorator_depends_q_foo():
    response = client.get("/decorator-depends/?q=foo")
    assert response.status_code == 200
    assert response.json() == {"in": "decorator-depends"}


def test_decorator_depends_q_foo_skip_100_limit_200():
    response = client.get("/decorator-depends/?q=foo&skip=100&limit=200")
    assert response.status_code == 200
    assert response.json() == {"in": "decorator-depends"}


def test_router_depends():
    response = client.get("/router-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "q"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_router_depends_q_foo():
    response = client.get("/router-depends/?q=foo")
    assert response.status_code == 200
    assert response.json() == {
        "in": "router-depends",
        "params": {"q": "foo", "skip": 0, "limit": 100},
    }


def test_router_depends_q_foo_skip_100_limit_200():
    response = client.get("/router-depends/?q=foo&skip=100&limit=200")
    assert response.status_code == 200
    assert response.json() == {
        "in": "router-depends",
        "params": {"q": "foo", "skip": 100, "limit": 200},
    }


def test_router_decorator_depends():
    response = client.get("/router-decorator-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "q"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_router_decorator_depends_q_foo():
    response = client.get("/router-decorator-depends/?q=foo")
    assert response.status_code == 200
    assert response.json() == {"in": "router-decorator-depends"}


def test_router_decorator_depends_q_foo_skip_100_limit_200():
    response = client.get("/router-decorator-depends/?q=foo&skip=100&limit=200")
    assert response.status_code == 200
    assert response.json() == {"in": "router-decorator-depends"}


@pytest.mark.parametrize(
    "url,status_code,expected",
    [
        (
            "/main-depends/",
            200,
            {"in": "main-depends", "params": {"q": None, "skip": 5, "limit": 10}},
        ),
        (
            "/main-depends/?q=foo",
            200,
            {"in": "main-depends", "params": {"q": "foo", "skip": 5, "limit": 10}},
        ),
        (
            "/main-depends/?q=foo&skip=100&limit=200",
            200,
            {"in": "main-depends", "params": {"q": "foo", "skip": 5, "limit": 10}},
        ),
        ("/decorator-depends/", 200, {"in": "decorator-depends"}),
        (
            "/router-depends/",
            200,
            {"in": "router-depends", "params": {"q": None, "skip": 5, "limit": 10}},
        ),
        (
            "/router-depends/?q=foo",
            200,
            {"in": "router-depends", "params": {"q": "foo", "skip": 5, "limit": 10}},
        ),
        (
            "/router-depends/?q=foo&skip=100&limit=200",
            200,
            {"in": "router-depends", "params": {"q": "foo", "skip": 5, "limit": 10}},
        ),
        ("/router-decorator-depends/", 200, {"in": "router-decorator-depends"}),
    ],
)
def test_override_simple(url, status_code, expected):
    app.dependency_overrides[common_parameters] = overrider_dependency_simple
    response = client.get(url)
    assert response.status_code == status_code
    assert response.json() == expected
    app.dependency_overrides = {}


def test_override_with_sub_main_depends():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/main-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub__main_depends_q_foo():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/main-depends/?q=foo")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_main_depends_k_bar():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/main-depends/?k=bar")
    assert response.status_code == 200
    assert response.json() == {"in": "main-depends", "params": {"k": "bar"}}
    app.dependency_overrides = {}


def test_override_with_sub_decorator_depends():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/decorator-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_decorator_depends_q_foo():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/decorator-depends/?q=foo")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_decorator_depends_k_bar():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/decorator-depends/?k=bar")
    assert response.status_code == 200
    assert response.json() == {"in": "decorator-depends"}
    app.dependency_overrides = {}


def test_override_with_sub_router_depends():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_router_depends_q_foo():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-depends/?q=foo")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_router_depends_k_bar():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-depends/?k=bar")
    assert response.status_code == 200
    assert response.json() == {"in": "router-depends", "params": {"k": "bar"}}
    app.dependency_overrides = {}


def test_override_with_sub_router_decorator_depends():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-decorator-depends/")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_router_decorator_depends_q_foo():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-decorator-depends/?q=foo")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "k"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }

    app.dependency_overrides = {}


def test_override_with_sub_router_decorator_depends_k_bar():
    app.dependency_overrides[common_parameters] = overrider_dependency_with_sub
    response = client.get("/router-decorator-depends/?k=bar")
    assert response.status_code == 200
    assert response.json() == {"in": "router-decorator-depends"}
    app.dependency_overrides = {}


def test_dependency_override_only_rebuilds_overridden_dependant(monkeypatch):
    local_app = FastAPI()

    def overridden_dep() -> str:
        return "original"  # pragma: no cover

    def target_dep() -> str:
        return "target"

    @local_app.get("/not-overridden")
    def not_overridden(val: str = Depends(target_dep)):
        return {"val": val}

    @local_app.get("/overridden")
    def overridden(val: str = Depends(overridden_dep)):
        return {"val": val}

    local_app.dependency_overrides[overridden_dep] = lambda: "overridden"

    get_dependant_calls = 0
    original_get_dependant = dependency_utils.get_dependant

    def counting_get_dependant(*args, **kwargs):
        nonlocal get_dependant_calls
        get_dependant_calls += 1
        return original_get_dependant(*args, **kwargs)

    monkeypatch.setattr(dependency_utils, "get_dependant", counting_get_dependant)

    local_client = TestClient(local_app)
    response = local_client.get("/not-overridden")
    assert response.status_code == 200
    assert response.json() == {"val": "target"}
    assert get_dependant_calls == 0

    response = local_client.get("/overridden")
    assert response.status_code == 200
    assert response.json() == {"val": "overridden"}
    assert get_dependant_calls == 1


def test_unrelated_dependency_override_does_not_change_security_scopes():
    local_app = FastAPI()

    def unrelated_dep() -> str:
        return "unrelated"  # pragma: no cover

    def child(security_scopes: SecurityScopes) -> list[str]:
        return security_scopes.scopes

    def parent(scopes: list[str] = Depends(child)) -> list[str]:
        return scopes

    def grandparent(scopes: list[str] = Security(parent, scopes=["a"])) -> list[str]:
        return scopes

    @local_app.get("/scopes")
    def endpoint(scopes: list[str] = Security(grandparent, scopes=["a"])):
        return scopes

    local_client = TestClient(local_app)
    response = local_client.get("/scopes")
    assert response.status_code == 200, response.text

    local_app.dependency_overrides[unrelated_dep] = lambda: "overridden"
    overridden_response = local_client.get("/scopes")
    assert overridden_response.status_code == 200, overridden_response.text
    assert overridden_response.json() == response.json()
