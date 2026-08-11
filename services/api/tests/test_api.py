from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.app.main import app


VALID_PAYLOAD = {
    "tail_number": "N104JB",
    "airline": "B6",
    "origin": "JFK",
    "destination": "BOS",
    "day_of_week": 1,
    "scheduled_departure_minutes": 960,
    "distance": 187,
}


@patch(
    "services.api.app.main.get_aircraft_state"
)
def test_prediction(
    mock_get_aircraft_state,
):

    mock_get_aircraft_state.return_value = {
        "tail_number": "N104JB",
        "current_airport": "JFK",
        "previous_flight_id": "B6419",
        "previous_arrival_delay": 42,
        "last_updated":
            "2026-08-10T22:00:00Z",
    }

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/predictions",
            json=VALID_PAYLOAD,
        )

        assert response.status_code == 200

        body = response.json()

        assert body["tail_number"] == "N104JB"

        assert (
            body[
                "current_aircraft_airport"
            ]
            == "JFK"
        )

        assert (
            body[
                "previous_arrival_delay"
            ]
            == 42
        )

        assert (
            body[
                "aircraft_position_match"
            ]
            is True
        )

        assert (
            0
            <= body[
                "delay_probability"
            ]
            <= 1
        )

        assert body["risk_level"] in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }


@patch(
    "services.api.app.main.get_aircraft_state"
)
def test_aircraft_position_mismatch(
    mock_get_aircraft_state,
):

    mock_get_aircraft_state.return_value = {
        "tail_number": "N104JB",
        "current_airport": "LAX",
        "previous_arrival_delay": 30,
    }

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/predictions",
            json=VALID_PAYLOAD,
        )

        assert response.status_code == 200

        body = response.json()

        assert (
            body[
                "aircraft_position_match"
            ]
            is False
        )


@patch(
    "services.api.app.main.get_aircraft_state"
)
def test_aircraft_not_found(
    mock_get_aircraft_state,
):

    mock_get_aircraft_state.return_value = None

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/predictions",
            json=VALID_PAYLOAD,
        )

        assert response.status_code == 404


def test_invalid_day():

    payload = VALID_PAYLOAD.copy()

    payload["day_of_week"] = 9

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/predictions",
            json=payload,
        )

        assert response.status_code == 422


def test_invalid_airport():

    payload = VALID_PAYLOAD.copy()

    payload["origin"] = "JF"

    with TestClient(app) as client:

        response = client.post(
            "/api/v1/predictions",
            json=payload,
        )

        assert response.status_code == 422