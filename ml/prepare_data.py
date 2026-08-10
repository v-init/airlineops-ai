from pathlib import Path

import numpy as np
import pandas as pd


RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")

OUTPUT_FILE = (
    PROCESSED_DATA_DIR
    / "flights_processed.parquet"
)


COLUMNS = [
    "FlightDate",
    "DayOfWeek",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Tail_Number",
    "Origin",
    "Dest",
    "CRSDepTime",
    "CRSArrTime",
    "Distance",
    "DepDelay",
    "ArrDelay",
    "Cancelled",
    "Diverted",
]


def hhmm_to_minutes(value):
    """
    Convert BTS HHMM time to minutes after midnight.

    Examples:
        930  -> 570
        1430 -> 870
        5    -> 5
        2400 -> 0
    """

    if pd.isna(value):
        return np.nan

    value = int(value)

    if value == 2400:
        return 0

    hours = value // 100
    minutes = value % 100

    if hours > 23 or minutes > 59:
        return np.nan

    return hours * 60 + minutes


def load_raw_data():
    files = sorted(
        RAW_DATA_DIR.glob("*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No CSV files found under data/raw"
        )

    print(
        f"Found {len(files)} raw CSV files."
    )

    frames = []

    for file_path in files:

        print(
            f"Loading {file_path.name}"
        )

        frame = pd.read_csv(
            file_path,
            usecols=COLUMNS,
            low_memory=False,
        )

        frames.append(frame)

    df = pd.concat(
        frames,
        ignore_index=True,
    )

    print(
        f"\nCombined raw rows: {len(df):,}"
    )

    return df


def clean_data(df):

    print("\nCleaning data...")

    # Convert date
    df["FlightDate"] = pd.to_datetime(
        df["FlightDate"],
        errors="coerce",
    )

    # Keep completed, non-diverted flights.
    df = df[
        (df["Cancelled"] == 0)
        & (df["Diverted"] == 0)
    ].copy()

    # We require an observed departure delay,
    # because this creates our training target.
    df = df[
        df["DepDelay"].notna()
    ].copy()

    # Important fields must exist.
    df = df.dropna(
        subset=[
            "FlightDate",
            "Reporting_Airline",
            "Origin",
            "Dest",
            "CRSDepTime",
            "Distance",
        ]
    )

    # Normalize string data
    string_columns = [
        "Reporting_Airline",
        "Tail_Number",
        "Origin",
        "Dest",
    ]

    for column in string_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    return df


def create_features(df):

    print("Creating features...")

    # Basic flight features
    df["scheduled_departure_minutes"] = (
        df["CRSDepTime"]
        .apply(hhmm_to_minutes)
    )


    df = df[
        df[
            "scheduled_departure_minutes"
        ].notna()
    ].copy()


    df["departure_hour"] = (
        df[
            "scheduled_departure_minutes"
        ]
        // 60
    ).astype(int)


    df["is_weekend"] = (
        df["DayOfWeek"]
        .isin([6, 7])
        .astype(int)
    )


    df["is_delayed"] = (
        df["DepDelay"] >= 15
    ).astype(int)
    
    # Create an actual timestamp for ordering flights.
    df[
        "scheduled_departure_datetime"
    ] = (
        df["FlightDate"]
        + pd.to_timedelta(
            df[
                "scheduled_departure_minutes"
            ],
            unit="m",
        )
    )


    # Sort flights chronologically
    # for each aircraft.
    df = df.sort_values(
        by=[
            "Tail_Number",
            "scheduled_departure_datetime",
        ],
        na_position="last",
    ).copy()


    aircraft_groups = df.groupby(
        "Tail_Number",
        dropna=True,
    )


    # Previous leg information.
    df["previous_tail_number"] = (
        aircraft_groups[
            "Tail_Number"
        ].shift(1)
    )


    df["previous_arrival_delay"] = (
        aircraft_groups[
            "ArrDelay"
        ].shift(1)
    )


    df["previous_destination"] = (
        aircraft_groups[
            "Dest"
        ].shift(1)
    )


    df[
        "previous_scheduled_departure_datetime"
    ] = (
        aircraft_groups[
            "scheduled_departure_datetime"
        ].shift(1)
    )


    # Explicit validation:
    # previous row must truly represent
    # an earlier flight of the same aircraft.
    same_aircraft = (
        df["Tail_Number"].notna()
        & df["previous_tail_number"].notna()
        & (
            df["Tail_Number"]
            == df["previous_tail_number"]
        )
    )


    previous_flight_is_earlier = (
        df[
            "previous_scheduled_departure_datetime"
        ].notna()
        &
        (
            df[
                "previous_scheduled_departure_datetime"
            ]
            <
            df[
                "scheduled_departure_datetime"
            ]
        )
    )


    airport_continuity = (
        df["previous_destination"]
        == df["Origin"]
    )


    time_since_previous_departure = (
        df[
            "scheduled_departure_datetime"
        ]
        -
        df[
            "previous_scheduled_departure_datetime"
        ]
    )


    recent_previous_flight = (
        time_since_previous_departure
        > pd.Timedelta(0)
    ) & (
        time_since_previous_departure
        <= pd.Timedelta(hours=24)
    )


    valid_previous_leg = (
        same_aircraft
        & previous_flight_is_earlier
        & airport_continuity
        & recent_previous_flight
    )


    df["valid_previous_leg"] = (
        valid_previous_leg.astype(int)
    )


    df["aircraft_position_match"] = (
        valid_previous_leg.astype(int)
    )


    # Invalid historical state should
    # not become an ML feature.
    df.loc[
        ~valid_previous_leg,
        "previous_arrival_delay",
    ] = 0


    df["previous_arrival_delay"] = (
        df[
            "previous_arrival_delay"
        ]
        .fillna(0)
        .clip(
            lower=-60,
            upper=600,
        )
    )

    return df


def select_output_columns(df):

    output_columns = [
        "FlightDate",
        "Reporting_Airline",
        "Tail_Number",
        "Origin",
        "Dest",
        "DayOfWeek",
        "scheduled_departure_minutes",
        "departure_hour",
        "Distance",
        "is_weekend",
        "previous_arrival_delay",
        "aircraft_position_match",
        "is_delayed",
    ]

    return df[output_columns].copy()


def main():

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_raw_data()

    df = clean_data(df)

    df = create_features(df)

    df = select_output_columns(df)

    print(
        f"\nFinal rows: {len(df):,}"
    )

    print(
        "\nDelay distribution:"
    )

    print(
        df["is_delayed"]
        .value_counts(
            normalize=True
        )
    )

    print(
        "\nMissing values:"
    )

    print(
        df.isna().sum()
    )

    df.to_parquet(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"\nSaved processed dataset to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()