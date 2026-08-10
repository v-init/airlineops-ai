from pathlib import Path

import pandas as pd


RAW_DATA_DIR = Path("data/raw")


files = list(RAW_DATA_DIR.glob("*.csv"))

if not files:
    raise FileNotFoundError(
        "No CSV files found in data/raw"
    )


print(f"Found {len(files)} CSV files")

first_file = files[0]

print(f"\nReading: {first_file.name}")


df = pd.read_csv(
    first_file,
    nrows=5
)


print("\nShape:")
print(df.shape)


print("\nColumns:")
for column in df.columns:
    print(column)


print("\nSample:")
print(df.head())