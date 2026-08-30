import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.user import create_random_user
from tests.utils.utils import random_email, random_lower_string

ROLE_FIXTURES = {
    "admin": "superuser_token_headers",
    "manager": "manager_token_headers",
    "member": "normal_user_token_headers",
}


def headers_for(request: pytest.FixtureRequest, role: str) -> dict[str, str]:
    return request.getfixturevalue(ROLE_FIXTURES[role])  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("manager", 200), ("member", 403)],
)
def test_list_users_role_matrix(
    client: TestClient, request: pytest.FixtureRequest, role: str, expected_status: int
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/", headers=headers_for(request, role))
    assert r.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("manager", 403), ("member", 403)],
)
def test_create_user_role_matrix(
    client: TestClient, request: pytest.FixtureRequest, role: str, expected_status: int
) -> None:
    payload = {"email": random_email(), "password": random_lower_string()}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=headers_for(request, role),
        json=payload,
    )
    assert r.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("manager", 200), ("member", 403)],
)
def test_read_other_user_role_matrix(
    client: TestClient,
    db: Session,
    request: pytest.FixtureRequest,
    role: str,
    expected_status: int,
) -> None:
    other_user = create_random_user(db)
    r = client.get(
        f"{settings.API_V1_STR}/users/{other_user.id}",
        headers=headers_for(request, role),
    )
    assert r.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("manager", 403), ("member", 403)],
)
def test_update_any_user_role_matrix(
    client: TestClient,
    db: Session,
    request: pytest.FixtureRequest,
    role: str,
    expected_status: int,
) -> None:
    other_user = create_random_user(db)
    r = client.patch(
        f"{settings.API_V1_STR}/users/{other_user.id}",
        headers=headers_for(request, role),
        json={"full_name": "Updated Name"},
    )
    assert r.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("manager", 200), ("member", 403)],
)
def test_metrics_summary_role_matrix(
    client: TestClient, request: pytest.FixtureRequest, role: str, expected_status: int
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/metrics/summary", headers=headers_for(request, role)
    )
    assert r.status_code == expected_status
    if expected_status == 200:
        summary = r.json()
        assert summary["total_users"] >= 1
        assert set(summary["users_by_role"]) == {"admin", "manager", "member"}


@pytest.mark.parametrize(
    ("method", "role", "expected_status"),
    [
        ("GET", "admin", 200),
        ("GET", "manager", 403),
        ("GET", "member", 403),
        ("PUT", "admin", 200),
        ("PUT", "manager", 403),
        ("PUT", "member", 403),
    ],
)
def test_global_settings_role_matrix(
    client: TestClient,
    request: pytest.FixtureRequest,
    method: str,
    role: str,
    expected_status: int,
) -> None:
    body = {"app_name": "Renamed App", "maintenance_mode": True}
    r = client.request(
        method,
        f"{settings.API_V1_STR}/settings/",
        headers=headers_for(request, role),
        json=body if method == "PUT" else None,
    )
    assert r.status_code == expected_status
    if method == "PUT" and expected_status == 200:
        assert r.json() == body


def test_protected_endpoint_without_token_returns_401(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/")
    assert r.status_code == 401


def test_invalid_token_returns_401(client: TestClient) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert r.status_code == 401


def test_member_can_read_and_update_own_profile(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "member"

    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json={"full_name": "Own New Name"},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Own New Name"


def test_member_cannot_escalate_own_role(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    # UserUpdateMe has no role field; a submitted role must be ignored
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json={"full_name": "Sneaky", "role": "admin"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "member"


def test_signup_assigns_member_role(client: TestClient) -> None:
    payload = {"email": random_email(), "password": random_lower_string()}
    r = client.post(f"{settings.API_V1_STR}/users/signup", json=payload)
    assert r.status_code == 200
    assert r.json()["role"] == "member"
