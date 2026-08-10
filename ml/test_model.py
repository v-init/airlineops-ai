import joblib
import pandas as pd


MODEL_FILE = (
    "artifacts/"
    "delay_model.joblib"
)


print(
    f"Loading model: "
    f"{MODEL_FILE}"
)


model = joblib.load(
    MODEL_FILE
)


flight = pd.DataFrame(
    [
        {
            "Reporting_Airline":
                "B6",

            "Origin":
                "JFK",

            "Dest":
                "BOS",

            "DayOfWeek":
                5,

            "scheduled_departure_minutes":
                960,

            "departure_hour":
                16,

            "Distance":
                187,

            "is_weekend":
                0,

            "previous_arrival_delay":
                90,

            "aircraft_position_match":
                1,
        }
    ]
)


probabilities = (
    model.predict_proba(
        flight
    )
)


delay_probability = (
    probabilities[0][1]
)


print(
    "\nPrediction:"
)

print(
    f"Delay probability: "
    f"{delay_probability:.4f}"
)


if delay_probability >= 0.70:

    risk = "HIGH"

elif delay_probability >= 0.40:

    risk = "MEDIUM"

else:

    risk = "LOW"


print(
    f"Risk level: {risk}"
)