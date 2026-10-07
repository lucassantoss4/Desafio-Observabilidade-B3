from fastapi.testclient import TestClient

from mock_provider.main import app


client = TestClient(app)


def test_validate_mode_success_returns_200() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200


def test_validate_success_json_contains_expected_fields() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 120,
        "server_load_percent": 35,
        "server_region": "sa-east-1",
    }


def test_validate_success_returns_received_ids() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_123", "movie_id": "mov_456"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "usr_123"
    assert payload["movie_id"] == "mov_456"


def test_validate_mode_error_returns_503() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2", "mode": "error"},
    )
    assert response.status_code == 503


def test_validate_mode_error_detail_is_correct() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2", "mode": "error"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "External validation service unavailable"}


def test_validate_with_invalid_mode_returns_422() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2", "mode": "invalid"},
    )
    assert response.status_code == 422


def test_validate_without_user_id_returns_422() -> None:
    response = client.get("/validate", params={"movie_id": "mov_dune_part2"})
    assert response.status_code == 422


def test_validate_without_movie_id_returns_422() -> None:
    response = client.get("/validate", params={"user_id": "usr_99823"})
    assert response.status_code == 422


def test_validate_with_empty_user_id_returns_422() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_validate_with_empty_movie_id_returns_422() -> None:
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": ""},
    )
    assert response.status_code == 422


def test_validate_with_user_id_larger_than_100_returns_422() -> None:
    long_user_id = "u" * 101
    response = client.get(
        "/validate",
        params={"user_id": long_user_id, "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_validate_with_movie_id_larger_than_100_returns_422() -> None:
    long_movie_id = "m" * 101
    response = client.get(
        "/validate",
        params={"user_id": "usr_99823", "movie_id": long_movie_id},
    )
    assert response.status_code == 422
