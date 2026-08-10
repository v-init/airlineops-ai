from fastapi.testclient import (
    TestClient,
)

from services.api.app.main import (
    app,
)


VALID_PAYLOAD = {

    "airline":
        "B6",

    "origin":
        "JFK",

    "destination":
        "BOS",

    "day_of_week":
        5,

    "scheduled_departure_minutes":
        960,

    "distance":
        187,

    "previous_arrival_delay":
        25,

    "aircraft_position_match":
        1,
}


def test_health():

    with TestClient(
        app
    ) as client:

        response = client.get(
            "/health"
        )

        assert (
            response.status_code
            == 200
        )

        body = response.json()

        assert (
            body["status"]
            == "ok"
        )

        assert (
            body[
                "model_loaded"
            ]
            is True
        )


def test_prediction():

    with TestClient(
        app
    ) as client:

        response = client.post(
            "/api/v1/predictions",
            json=VALID_PAYLOAD,
        )

        assert (
            response.status_code
            == 200
        )

        body = (
            response.json()
        )

        assert (
            0
            <= body[
                "delay_probability"
            ]
            <= 1
        )

        assert (
            body[
                "risk_level"
            ]
            in {
                "LOW",
                "MEDIUM",
                "HIGH",
            }
        )

        assert (
            isinstance(
                body[
                    "predicted_delayed"
                ],
                bool,
            )
        )


def test_invalid_day():

    payload = (
        VALID_PAYLOAD.copy()
    )

    payload[
        "day_of_week"
    ] = 9


    with TestClient(
        app
    ) as client:

        response = client.post(
            "/api/v1/predictions",
            json=payload,
        )

        assert (
            response.status_code
            == 422
        )


def test_invalid_airport():

    payload = (
        VALID_PAYLOAD.copy()
    )

    payload["origin"] = "JF"


    with TestClient(
        app
    ) as client:

        response = client.post(
            "/api/v1/predictions",
            json=payload,
        )

        assert (
            response.status_code
            == 422
        )


def test_lowercase_airports():

    payload = (
        VALID_PAYLOAD.copy()
    )

    payload["origin"] = "jfk"

    payload[
        "destination"
    ] = "bos"


    with TestClient(
        app
    ) as client:

        response = client.post(
            "/api/v1/predictions",
            json=payload,
        )

        assert (
            response.status_code
            == 200
        )