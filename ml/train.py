import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import (
    ColumnTransformer,
)

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from sklearn.pipeline import (
    Pipeline,
)

from sklearn.preprocessing import (
    OneHotEncoder,
)

from xgboost import (
    XGBClassifier,
)


DATA_FILE = Path(
    "data/processed/"
    "flights_processed.parquet"
)

ARTIFACT_DIR = Path(
    "artifacts"
)

MODEL_FILE = (
    ARTIFACT_DIR
    / "delay_model.joblib"
)

METRICS_FILE = (
    ARTIFACT_DIR
    / "metrics.json"
)


CATEGORICAL_FEATURES = [
    "Reporting_Airline",
    "Origin",
    "Dest",
]


NUMERIC_FEATURES = [
    "DayOfWeek",
    "scheduled_departure_minutes",
    "departure_hour",
    "Distance",
    "is_weekend",
    "previous_arrival_delay",
    "aircraft_position_match",
]


FEATURES = (
    CATEGORICAL_FEATURES
    + NUMERIC_FEATURES
)


TARGET = "is_delayed"


TRAIN_END_DATE = (
    "2025-04-30"
)

TEST_START_DATE = (
    "2025-05-01"
)


def load_data():

    print(
        f"Loading data from:"
        f"\n{DATA_FILE}"
    )

    df = pd.read_parquet(
        DATA_FILE
    )

    df["FlightDate"] = (
        pd.to_datetime(
            df["FlightDate"]
        )
    )

    df = df.sort_values(
        "FlightDate"
    ).reset_index(
        drop=True
    )

    print(
        f"\nTotal rows: "
        f"{len(df):,}"
    )

    print(
        "\nDate range:"
    )

    print(
        df["FlightDate"].min(),
        "to",
        df["FlightDate"].max(),
    )

    return df


def split_data(df):

    train_df = df[
        df["FlightDate"]
        <= TRAIN_END_DATE
    ].copy()

    test_df = df[
        df["FlightDate"]
        >= TEST_START_DATE
    ].copy()


    print(
        "\nTraining rows:",
        f"{len(train_df):,}"
    )

    print(
        "Testing rows:",
        f"{len(test_df):,}"
    )


    print(
        "\nTraining period:"
    )

    print(
        train_df[
            "FlightDate"
        ].min(),
        "to",
        train_df[
            "FlightDate"
        ].max(),
    )


    print(
        "\nTesting period:"
    )

    print(
        test_df[
            "FlightDate"
        ].min(),
        "to",
        test_df[
            "FlightDate"
        ].max(),
    )


    X_train = (
        train_df[FEATURES]
    )

    y_train = (
        train_df[TARGET]
    )


    X_test = (
        test_df[FEATURES]
    )

    y_test = (
        test_df[TARGET]
    )


    print(
        "\nTraining target distribution:"
    )

    print(
        y_train
        .value_counts(
            normalize=True
        )
    )


    print(
        "\nTesting target distribution:"
    )

    print(
        y_test
        .value_counts(
            normalize=True
        )
    )


    return (
        X_train,
        X_test,
        y_train,
        y_test,
    )


def build_pipeline():

    categorical_transformer = (
        OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=True,
        )
    )


    preprocessor = (
        ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    categorical_transformer,
                    CATEGORICAL_FEATURES,
                ),
                (
                    "numeric",
                    "passthrough",
                    NUMERIC_FEATURES,
                ),
            ]
        )
    )


    classifier = (
        XGBClassifier(
            n_estimators=250,

            max_depth=5,

            learning_rate=0.08,

            subsample=0.8,

            colsample_bytree=0.8,

            eval_metric="logloss",

            tree_method="hist",

            n_jobs=-1,

            random_state=42,
        )
    )


    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )


    return pipeline


def evaluate_model(
    model,
    X_test,
    y_test,
):

    print(
        "\nGenerating predictions..."
    )


    probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )


    threshold = 0.50


    predictions = (
        probabilities
        >= threshold
    ).astype(int)


    metrics = {

        "threshold":
            threshold,

        "accuracy":
            float(
                accuracy_score(
                    y_test,
                    predictions,
                )
            ),

        "precision":
            float(
                precision_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),

        "recall":
            float(
                recall_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),

        "f1":
            float(
                f1_score(
                    y_test,
                    predictions,
                    zero_division=0,
                )
            ),

        "roc_auc":
            float(
                roc_auc_score(
                    y_test,
                    probabilities,
                )
            ),

        "pr_auc":
            float(
                average_precision_score(
                    y_test,
                    probabilities,
                )
            ),
    }


    print(
        "\n======================"
    )

    print(
        "MODEL METRICS"
    )

    print(
        "======================"
    )


    for name, value in (
        metrics.items()
    ):

        print(
            f"{name:12}: "
            f"{value:.4f}"
        )


    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            digits=4,
        )
    )


    print(
        "\nConfusion matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            predictions,
        )
    )


    return metrics


def save_artifacts(
    model,
    metrics,
):

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    joblib.dump(
        model,
        MODEL_FILE,
    )


    print(
        f"\nSaved model to:"
        f"\n{MODEL_FILE}"
    )


    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metrics,
            file,
            indent=2,
        )


    print(
        f"\nSaved metrics to:"
        f"\n{METRICS_FILE}"
    )


def main():

    df = load_data()

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = split_data(df)


    print(
        "\nBuilding ML pipeline..."
    )

    model = build_pipeline()


    print(
        "\nTraining XGBoost..."
    )

    model.fit(
        X_train,
        y_train,
    )


    metrics = evaluate_model(
        model,
        X_test,
        y_test,
    )


    save_artifacts(
        model,
        metrics,
    )


if __name__ == "__main__":
    main()