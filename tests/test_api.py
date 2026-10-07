from fastapi.testclient import TestClient

from app.main import app


# TestClient executa a aplicação ASGI em memória e permite validar a API sem
# iniciar um processo Uvicorn real.
client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_payload() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "stream-authorization-api",
    }


def test_stream_authorize_with_valid_params_returns_200() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200


def test_stream_authorize_valid_response_contains_all_fields() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    payload = response.json()

    expected_fields = {
        "user_id",
        "movie_id",
        "authorized",
        "resolution",
        "drm_token",
        "server_region",
    }

    assert response.status_code == 200
    assert expected_fields.issubset(payload.keys())


def test_stream_authorize_authorized_is_true() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["authorized"] is True


def test_stream_authorize_resolution_is_4k() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["resolution"] == "4K"


def test_stream_authorize_server_region_is_sa_east_1() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["server_region"] == "sa-east-1"


def test_stream_authorize_without_user_id_returns_422() -> None:
    response = client.get("/stream/authorize", params={"movie_id": "mov_dune_part2"})
    assert response.status_code == 422


def test_stream_authorize_without_movie_id_returns_422() -> None:
    response = client.get("/stream/authorize", params={"user_id": "usr_99823"})
    assert response.status_code == 422


def test_stream_authorize_with_empty_user_id_returns_422() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_stream_authorize_with_empty_movie_id_returns_422() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": ""},
    )
    assert response.status_code == 422


def test_stream_authorize_with_user_id_larger_than_100_returns_422() -> None:
    # O contrato aceita até 100 caracteres; 101 valida o primeiro valor fora do
    # limite permitido.
    long_user_id = "u" * 101
    response = client.get(
        "/stream/authorize",
        params={"user_id": long_user_id, "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_stream_authorize_with_movie_id_larger_than_100_returns_422() -> None:
    # A mesma regra vale para movie_id: 101 caracteres deve falhar no mesmo
    # limite máximo.
    long_movie_id = "m" * 101
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": long_movie_id},
    )
    assert response.status_code == 422
