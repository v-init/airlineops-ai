from contextlib import asynccontextmanager
from pathlib import Path

import boto3
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


AWS_REGION = "us-east-1"

DYNAMODB_TABLE = (
    "airlineops-aircraft-state"
)


model = None


# ---------------------------------------------------------
# DynamoDB
# ---------------------------------------------------------

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
)

aircraft_table = dynamodb.Table(
    DYNAMODB_TABLE
)


# ---------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Request schema
# ---------------------------------------------------------

class FlightPredictionRequest(
    BaseModel
):

    tail_number: str = Field(
        min_length=4,
        max_length=10,
        examples=["N104JB"],
    )

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


# ---------------------------------------------------------
# Response schema
# ---------------------------------------------------------

class PredictionResponse(
    BaseModel
):

    tail_number: str

    current_aircraft_airport: str

    previous_arrival_delay: float

    aircraft_position_match: bool

    delay_probability: float

    predicted_delayed: bool

    risk_level: str

    classification_threshold: float

    model_version: str


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def classify_risk(
    probability: float,
):

    if probability >= 0.70:
        return "HIGH"

    if probability >= 0.40:
        return "MEDIUM"

    return "LOW"


def get_aircraft_state(
    tail_number: str,
):

    response = (
        aircraft_table.get_item(

            Key={
                "tail_number":
                    tail_number.upper()
            },

            ConsistentRead=True,
        )
    )

    return response.get(
        "Item"
    )


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Prediction endpoint
# ---------------------------------------------------------

@app.post(
    "/api/v1/predictions",
    response_model=
        PredictionResponse,
)
def predict_delay(
    request:
        FlightPredictionRequest,
):

    # ---------------------------------
    # Check model availability
    # ---------------------------------

    if model is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Prediction model "
                "is unavailable."
            ),
        )


    # ---------------------------------
    # Fetch live aircraft state
    # ---------------------------------

    aircraft_state = (
        get_aircraft_state(
            request.tail_number
        )
    )


    if aircraft_state is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Aircraft state not found "
                f"for {request.tail_number}"
            ),
        )


    # ---------------------------------
    # Extract online features
    # ---------------------------------

    previous_arrival_delay = float(
        aircraft_state.get(
            "previous_arrival_delay",
            0,
        )
    )


    current_airport = (
        aircraft_state.get(
            "current_airport"
        )
    )


    aircraft_position_match = int(
        current_airport
        == request.origin.upper()
    )


    # ---------------------------------
    # Derive scheduled features
    # ---------------------------------

    departure_hour = (
        request
        .scheduled_departure_minutes
        // 60
    )


    is_weekend = int(
        request.day_of_week
        in (6, 7)
    )


    # ---------------------------------
    # Build model input
    # ---------------------------------

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
                    previous_arrival_delay,

                "aircraft_position_match":
                    aircraft_position_match,
            }
        ]
    )


    # ---------------------------------
    # ML inference
    # ---------------------------------

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


    # ---------------------------------
    # Response
    # ---------------------------------

    return PredictionResponse(

        tail_number=
            request
            .tail_number
            .upper(),

        current_aircraft_airport=
            current_airport,

        previous_arrival_delay=
            previous_arrival_delay,

        aircraft_position_match=
            bool(
                aircraft_position_match
            ),

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