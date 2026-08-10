from contextlib import (
    asynccontextmanager,
)

from pathlib import Path

import joblib
import pandas as pd

from fastapi import (
    FastAPI,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)


MODEL_PATH = Path(
    "artifacts/"
    "delay_model.joblib"
)


model = None


@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    global model

    print(
        f"Loading model from "
        f"{MODEL_PATH}"
    )


    if not MODEL_PATH.exists():

        raise RuntimeError(
            f"Model file not found: "
            f"{MODEL_PATH}"
        )


    model = joblib.load(
        MODEL_PATH
    )


    print(
        "Model loaded successfully"
    )


    yield


    model = None


app = FastAPI(

    title=
        "AirlineOps AI",

    description=(
        "Real-time airline "
        "flight-delay prediction API"
    ),

    version=
        "1.0.0",

    lifespan=
        lifespan,
)


class FlightPredictionRequest(
    BaseModel
):

    airline: str = Field(
        min_length=2,
        max_length=3,
        examples=["B6"],
    )

    origin: str = Field(
        min_length=3,
        max_length=3,
        examples=["JFK"],
    )

    destination: str = Field(
        min_length=3,
        max_length=3,
        examples=["BOS"],
    )

    day_of_week: int = Field(
        ge=1,
        le=7,
    )

    scheduled_departure_minutes: int = (
        Field(
            ge=0,
            le=1439,
            examples=[960],
        )
    )

    distance: float = Field(
        gt=0,
        examples=[187],
    )

    previous_arrival_delay: float = (
        Field(
            default=0,
            examples=[35],
        )
    )

    aircraft_position_match: int = (
        Field(
            default=1,
            ge=0,
            le=1,
        )
    )


class PredictionResponse(
    BaseModel
):

    delay_probability: float

    predicted_delayed: bool

    risk_level: str

    classification_threshold: float

    model_version: str


def classify_risk(
    probability: float,
):

    if probability >= 0.70:
        return "HIGH"

    if probability >= 0.40:
        return "MEDIUM"

    return "LOW"


@app.get(
    "/health"
)
def health():

    return {
        "status": "ok",

        "model_loaded":
            model is not None,

        "service":
            "airlineops-ai",
    }


@app.post(
    "/api/v1/predictions",
    response_model=
        PredictionResponse,
)
def predict_delay(
    request:
        FlightPredictionRequest,
):

    if model is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction model "
                "is unavailable."
            ),
        )


    departure_hour = (
        request
        .scheduled_departure_minutes
        // 60
    )


    is_weekend = int(
        request.day_of_week
        in (6, 7)
    )


    features = pd.DataFrame(
        [
            {
                "Reporting_Airline":
                    request
                    .airline
                    .upper(),

                "Origin":
                    request
                    .origin
                    .upper(),

                "Dest":
                    request
                    .destination
                    .upper(),

                "DayOfWeek":
                    request
                    .day_of_week,

                "scheduled_departure_minutes":
                    request
                    .scheduled_departure_minutes,

                "departure_hour":
                    departure_hour,

                "Distance":
                    request
                    .distance,

                "is_weekend":
                    is_weekend,

                "previous_arrival_delay":
                    request
                    .previous_arrival_delay,

                "aircraft_position_match":
                    request
                    .aircraft_position_match,
            }
        ]
    )


    probability = float(
        model.predict_proba(
            features
        )[0][1]
    )


    threshold = 0.50


    predicted_delayed = (
        probability
        >= threshold
    )


    return PredictionResponse(

        delay_probability=
            round(
                probability,
                4,
            ),

        predicted_delayed=
            bool(
                predicted_delayed
            ),

        risk_level=
            classify_risk(
                probability
            ),

        classification_threshold=
            threshold,

        model_version=
            "local-v1",
    )