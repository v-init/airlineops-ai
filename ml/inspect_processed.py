import pandas as pd


DATA_FILE = (
    "data/processed/"
    "flights_processed.parquet"
)


df = pd.read_parquet(
    DATA_FILE
)


print("\nShape:")
print(df.shape)


print("\nColumns:")
print(df.columns.tolist())


print("\nFirst 10 rows:")
print(
    df.head(10)
    .to_string(index=False)
)


print("\nData types:")
print(df.dtypes)


print("\nDelay distribution:")
print(
    df["is_delayed"]
    .value_counts()
)

print(
    df["is_delayed"]
    .value_counts(normalize=True)
)


print(
    "\nPrevious arrival delay stats:"
)

print(
    df[
        "previous_arrival_delay"
    ].describe()
)


print(
    "\nAircraft position match:"
)

print("Counts:")
print(
    df[
        "aircraft_position_match"
    ]
    .value_counts()
)

print("\nPercentages:")
print(
    df[
        "aircraft_position_match"
    ]
    .value_counts(
        normalize=True
    )
)


print(
    "\nDate range:"
)

print(
    df["FlightDate"].min()
)

print(
    df["FlightDate"].max()
)