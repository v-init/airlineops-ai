# AirlineOps AI

AirlineOps AI is a production-style real-time airline flight-delay prediction platform built with Python, XGBoost, FastAPI, Kafka-compatible event streaming, Amazon DynamoDB, Docker, Amazon ECR, GitHub Actions, and AWS.

The system predicts whether an upcoming flight is likely to depart at least 15 minutes late using both scheduled flight information and real-time operational state from the aircraft's previous leg.

---

## Problem

Flight delays are influenced not only by scheduled flight characteristics but also by operational conditions from previous aircraft legs.

For example, if an aircraft arrives late from its previous flight, the next flight may also be delayed because of reduced turnaround time.

This project combines:

- historical airline flight data
- machine learning
- real-time aircraft event streaming
- shared operational state
- backend APIs
- cloud infrastructure
- automated testing and CI

to build an end-to-end flight-delay prediction system.

The prediction target is:

```text
Departure Delay >= 15 minutes
```

A flight meeting this condition is classified as delayed.

---

## Architecture

```text
                         OFFLINE ML PIPELINE

                    U.S. DOT BTS Flight Data
                              |
                              v
                     Data Preprocessing
                              |
                              v
                     Feature Engineering
                              |
                              v
                       XGBoost Model
                              |
                              v
                  artifacts/delay_model.joblib


                       ONLINE PIPELINE

                 Aircraft Event Simulator
                              |
                              v
                     Kafka / Redpanda
                        flight-events
                              |
                              v
                    Stateful Consumer
                              |
                              v
                     Amazon DynamoDB
                airlineops-aircraft-state
                              |
                              v
                         FastAPI
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
       Flight Request                   Aircraft State
                                             Lookup
             |                                 |
             +----------------+----------------+
                              |
                              v
                      Feature Assembly
                              |
                              v
                        XGBoost Model
                              |
                              v
                     Delay Probability


                         DEVOPS

                         GitHub
                            |
                            v
                     GitHub Actions
                      /           \
                     v             v
                  pytest       Docker Build
                                    |
                                    v
                               Amazon ECR
```

---

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Machine Learning | XGBoost, scikit-learn |
| Data Processing | pandas |
| API | FastAPI |
| Event Streaming | Redpanda / Kafka API |
| Online State Store | Amazon DynamoDB |
| Containerization | Docker |
| Container Registry | Amazon ECR |
| CI | GitHub Actions |
| Testing | pytest, FastAPI TestClient |
| Cloud | AWS |
| Dataset | U.S. DOT Bureau of Transportation Statistics |

---

## Dataset

The machine-learning model is trained using the U.S. Department of Transportation Bureau of Transportation Statistics Reporting Carrier On-Time Performance dataset.

For this prototype, six months of flight data from January through June 2025 were used.

### Dataset Size

Raw records:

```text
3,446,676
```

Processed records:

```text
3,385,822
```

### Target

The binary target is:

```text
is_delayed = 1
```

when:

```text
DepDelay >= 15 minutes
```

Otherwise:

```text
is_delayed = 0
```

### Target Distribution

The processed dataset contains approximately:

```text
Non-delayed flights: 78.98%
Delayed flights:     21.02%
```

Because the dataset is imbalanced, model evaluation includes metrics beyond accuracy, including:

- Precision
- Recall
- F1 score
- ROC-AUC
- PR-AUC

---

## Leakage Prevention

Only features intended to be available before the current flight departs are used for prediction.

Current-flight outcome fields are intentionally excluded, including:

- current departure-delay indicators
- current arrival-delay indicators
- carrier delay
- weather delay
- NAS delay
- late-aircraft delay
- current-flight outcome information

The previous aircraft leg is included only when it can be chronologically and operationally matched to the current flight.

A valid previous leg must satisfy conditions such as:

- same aircraft tail number
- previous scheduled departure occurs before the current flight
- previous destination matches the current origin
- previous leg is sufficiently recent

This prevents future or current-flight information from leaking into the prediction model.

---

## Model Features

### Scheduled Flight Features

The model uses:

- Reporting airline
- Origin airport
- Destination airport
- Day of week
- Scheduled departure time in minutes
- Departure hour
- Flight distance
- Weekend indicator

### Real-Time Aircraft Features

Two aircraft operational features are used:

```text
previous_arrival_delay
```

This represents the arrival delay of the aircraft's previous valid flight.

```text
aircraft_position_match
```

This indicates whether the aircraft's latest known airport matches the origin airport of the upcoming flight.

For example:

```text
Aircraft current airport: JFK
Upcoming flight origin:   JFK

aircraft_position_match = 1
```

If the locations do not match:

```text
aircraft_position_match = 0
```

---

## Model Training

Categorical features such as airline, origin, and destination are encoded using a scikit-learn preprocessing pipeline.

The classifier is an XGBoost binary classifier.

The preprocessing logic and trained classifier are stored together as a serialized model pipeline:

```text
artifacts/delay_model.joblib
```

This allows the FastAPI service to provide raw feature values directly to the saved pipeline without recreating encoding logic at inference time.

---

## Model Evaluation Strategy

The dataset is split chronologically instead of randomly.

Training period:

```text
January 2025 - April 2025
```

Testing period:

```text
May 2025 - June 2025
```

A temporal split better represents the production scenario where historical flights are used to predict future flights.

It also reduces the risk of temporal leakage that could occur when later flights are randomly mixed into the training dataset.

---

## Model Performance

Model metrics are stored in:

```text
artifacts/metrics.json
```

Replace the values below with the metrics from that file.

| Metric | Score |
|---|---:|
| Accuracy | 0.8408 |
| Precision | 0.8225 |
| Recall | 0.4608 |
| F1 | 0.5907` |
| ROC-AUC | 0.8292 |
| PR-AUC | 0.7127 |

Accuracy should not be interpreted alone because approximately 79% of flights in the dataset belong to the non-delayed class.

---

## Real-Time Event Processing

The system includes a Python aircraft-event simulator.

The producer generates synthetic aircraft arrival events such as:

```json
{
  "event_id": "15976159-206f-431c-ab4e-f82f8e10b107",
  "event_type": "AIRCRAFT_ARRIVED",
  "event_time": "2026-08-10T22:26:16.487570+00:00",
  "flight_id": "B6305",
  "tail_number": "N102JB",
  "origin": "BOS",
  "destination": "ATL",
  "arrival_delay_minutes": 10
}
```

Events are published to:

```text
flight-events
```

through Redpanda using the Kafka protocol.

---

## Kafka Design

The prototype uses a single Kafka partition because throughput and horizontal scaling are not goals of the two-day demo.

Events are still keyed by aircraft tail number:

```text
key = tail_number
```

For example:

```text
N101JB
N102JB
N103JB
N104JB
```

Using the aircraft tail number as the event key reflects how the system could scale to multiple partitions.

In a multi-partition deployment, events belonging to the same aircraft could be consistently routed together, preserving aircraft-specific ordering within a partition.

---

## Why Tail Number?

A flight number represents a scheduled service.

A tail number represents the physical aircraft.

The physical aircraft matters because operational delay can propagate between consecutive flights flown by the same aircraft.

For example:

```text
Flight 1

BOS -> JFK
Aircraft: N104JB
Arrival delay: 45 minutes

            |
            v

Flight 2

JFK -> MCO
Aircraft: N104JB
```

The previous arrival delay may increase the risk that Flight 2 departs late.

---

## Aircraft State Processing

A stateful Python consumer reads `AIRCRAFT_ARRIVED` events from the Kafka topic.

For each event, the consumer derives the latest aircraft state and stores it in Amazon DynamoDB.

The persisted state contains:

- tail number
- current airport
- previous flight ID
- previous arrival delay
- last update timestamp

Example:

```json
{
  "tail_number": "N104JB",
  "current_airport": "JFK",
  "previous_flight_id": "B6419",
  "previous_arrival_delay": 13,
  "last_updated": "2026-08-10T22:26:34.493659+00:00"
}
```

---

## DynamoDB

Aircraft state is stored in:

```text
airlineops-aircraft-state
```

The partition key is:

```text
tail_number
```

### Why DynamoDB?

The primary online access pattern is:

> Retrieve the latest operational state for one aircraft using its tail number.

This maps naturally to a key-value NoSQL access pattern.

Instead of keeping aircraft state inside the consumer process, state is externalized into DynamoDB so it can be shared between independent services.

The architecture therefore becomes:

```text
Kafka Consumer
      |
      v
  DynamoDB
      ^
      |
    FastAPI
```

The consumer writes state asynchronously while FastAPI reads that state synchronously during prediction requests.

---

## Prediction API

The backend is implemented using FastAPI.

Available endpoints:

```text
GET /health
```

and:

```text
POST /api/v1/predictions
```

### Health Endpoint

Example:

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "service": "airlineops-ai"
}
```

---

## Prediction Request

The prediction endpoint receives scheduled flight information plus the physical aircraft tail number.

Example:

```json
{
  "tail_number": "N104JB",
  "airline": "B6",
  "origin": "JFK",
  "destination": "BOS",
  "day_of_week": 1,
  "scheduled_departure_minutes": 960,
  "distance": 187
}
```

The caller does not provide:

```text
previous_arrival_delay
aircraft_position_match
```

These are derived by the backend from the live aircraft state.

---

## Online Inference Flow

When a prediction request arrives:

1. FastAPI receives the upcoming flight information.
2. The API extracts the aircraft tail number.
3. DynamoDB is queried using the tail number.
4. The latest aircraft location is retrieved.
5. The previous arrival delay is retrieved.
6. The current aircraft airport is compared with the upcoming flight origin.
7. `aircraft_position_match` is generated.
8. Scheduled features are derived.
9. All features are assembled into a pandas DataFrame.
10. The serialized XGBoost pipeline performs inference.
11. The API returns the delay probability and risk classification.

Conceptually:

```text
Prediction Request
       |
       v
tail_number = N104JB
       |
       v
DynamoDB Lookup
       |
       +--> current_airport = JFK
       |
       +--> previous_arrival_delay = 42
       |
       v
Upcoming origin = JFK
       |
       v
aircraft_position_match = 1
       |
       v
Feature Assembly
       |
       v
XGBoost
       |
       v
Delay Probability
```

---

## Prediction Response

Example response:

```json
{
  "tail_number": "N104JB",
  "current_aircraft_airport": "JFK",
  "previous_arrival_delay": 42.0,
  "aircraft_position_match": true,
  "delay_probability": 0.63,
  "predicted_delayed": true,
  "risk_level": "MEDIUM",
  "classification_threshold": 0.5,
  "model_version": "local-v1"
}
```

The probability above is an example. Replace it with an actual response from your model if desired.

### Risk Levels

The API maps prediction probabilities to human-readable risk categories:

```text
Probability < 0.40
LOW
```

```text
0.40 <= Probability < 0.70
MEDIUM
```

```text
Probability >= 0.70
HIGH
```

The binary classification threshold is:

```text
0.50
```

---

## Testing

The API is tested using:

- pytest
- FastAPI TestClient
- Python mocking

DynamoDB access is mocked during unit testing so tests do not depend on live AWS infrastructure.

Test coverage includes scenarios such as:

- successful flight-delay prediction
- aircraft position match
- aircraft position mismatch
- missing aircraft state
- invalid day-of-week values
- invalid airport codes
- model response validation

Example:

```bash
pytest -v
```

With coverage:

```bash
pytest --cov=services.api --cov-report=term-missing -v
```

---

## Continuous Integration

GitHub Actions runs automatically for:

```text
push -> main
```

and:

```text
pull request -> main
```

The CI workflow:

1. Checks out the repository
2. Configures Python 3.11
3. Installs project dependencies
4. Runs pytest
5. Builds the Docker image

The pipeline ensures that changes must successfully pass automated tests and container-build validation.

Conceptually:

```text
Git Push / Pull Request
          |
          v
     GitHub Actions
          |
          v
   Install Dependencies
          |
          v
        pytest
          |
          v
     Docker Build
```

---

## Containerization

The FastAPI inference service is packaged as a Docker image.

The image contains:

- FastAPI application
- application dependencies
- serialized ML model
- inference code

Example build:

```bash
docker build -t airlineops-api:local .
```

Example local run:

```powershell
docker run `
    --rm `
    --name airlineops-api `
    -p 8000:8000 `
    -v "${HOME}\.aws:/root/.aws:ro" `
    -e AWS_DEFAULT_REGION=us-east-1 `
    airlineops-api:local
```

AWS credentials are not embedded in the Docker image.

---

## Running Locally

### Prerequisites

Install:

- Python 3.11
- Docker Desktop
- AWS CLI
- Git
- AWS credentials with DynamoDB access

---

### 1. Clone the Repository

```bash
git clone <repository-url>
cd airlineops-ai
```

---

### 2. Create a Python Virtual Environment

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure AWS

Verify your AWS identity:

```bash
aws sts get-caller-identity
```

The application expects the DynamoDB table:

```text
airlineops-aircraft-state
```

in:

```text
us-east-1
```

---

### 5. Start Redpanda

```bash
docker compose up -d
```

Verify:

```bash
docker ps
```

---

### 6. Start the Stream Processor

```bash
python services/stream_processor/consumer.py
```

The consumer will read events and persist aircraft state to DynamoDB.

---

### 7. Start the Aircraft Event Producer

In another terminal:

```bash
python services/event_producer/producer.py
```

Example producer output:

```text
Publishing event:

AIRCRAFT_ARRIVED
N104JB
BOS -> JFK
arrival_delay_minutes = 42
```

---

### 8. Start FastAPI

In another terminal:

```bash
uvicorn services.api.app.main:app --reload --port 8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

---

### 9. Submit a Prediction

If DynamoDB contains:

```text
tail_number = N104JB
current_airport = JFK
previous_arrival_delay = 42
```

submit:

```json
{
  "tail_number": "N104JB",
  "airline": "B6",
  "origin": "JFK",
  "destination": "BOS",
  "day_of_week": 1,
  "scheduled_departure_minutes": 960,
  "distance": 187
}
```

The API will retrieve:

```text
previous_arrival_delay = 42
```

from DynamoDB and automatically calculate:

```text
aircraft_position_match = true
```

before running the ML model.

---

## End-to-End Demo Flow

The full runtime flow is:

```text
1. Aircraft event generated

N104JB
BOS -> JFK
Arrival delay = 42 minutes

            |
            v

2. Event published to Kafka

flight-events

            |
            v

3. Stateful consumer processes event

            |
            v

4. DynamoDB updated

N104JB
current_airport = JFK
previous_arrival_delay = 42

            |
            v

5. Upcoming flight prediction requested

N104JB
JFK -> BOS

            |
            v

6. FastAPI queries DynamoDB

            |
            v

7. Online features generated

previous_arrival_delay = 42
aircraft_position_match = 1

            |
            v

8. XGBoost inference

            |
            v

9. Delay probability returned
```

This demonstrates an end-to-end online ML inference architecture rather than only serving a static machine-learning model.

---

## Project Structure

```text
airlineops-ai/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── artifacts/
│   ├── delay_model.joblib
│   └── metrics.json
│
├── data/
│   ├── raw/
│   └── processed/
│
├── ml/
│   ├── prepare_data.py
│   └── train.py
│
├── services/
│   │
│   ├── api/
│   │   ├── app/
│   │   │   └── main.py
│   │   │
│   │   └── tests/
│   │       └── test_api.py
│   │
│   ├── event_producer/
│   │   └── producer.py
│   │
│   └── stream_processor/
│       └── consumer.py
│
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

The `data/` directory is excluded from Git because the underlying airline dataset is large.

---

## Key Design Decisions

### Temporal Train/Test Split

A chronological split is used rather than a random split to better simulate production, where future flights are predicted using historical observations.

---

### Separate Asynchronous and Synchronous Workloads

Aircraft operational events are asynchronous.

Prediction requests are synchronous.

Kafka handles the asynchronous event path:

```text
Aircraft Events
      |
      v
Kafka
      |
      v
State Consumer
```

FastAPI handles synchronous inference:

```text
Client
  |
  v
FastAPI
  |
  v
Prediction
```

This keeps event ingestion separate from prediction serving.

---

### Externalized Aircraft State

The Kafka consumer and FastAPI application run as separate processes.

Aircraft state therefore cannot safely remain inside an in-memory Python dictionary.

DynamoDB provides shared persistent state accessible by both components.

---

### Tail Number as State Key

The physical aircraft tail number is used as the primary state identifier because delay propagation occurs between flights operated by the same physical aircraft.

---

### Model Pipeline Artifact

The trained preprocessing pipeline and XGBoost model are serialized together.

This reduces training-serving skew because categorical transformations used during training are reused during inference.

---

### Single Kafka Partition

The demo intentionally uses one partition because throughput is not the objective.

The application still uses tail number as the Kafka key so the architecture can naturally evolve toward multi-partition processing.

---

## Prototype Scope

This project was intentionally scoped as a two-day production-style prototype.

The goal was to demonstrate the complete path from historical model training to online operational inference rather than fully productionize every component.

Implemented:

- historical airline-data preprocessing
- leakage-aware feature engineering
- XGBoost classifier
- temporal model evaluation
- FastAPI inference service
- Kafka-compatible event producer
- stateful event consumer
- DynamoDB online state
- Docker containerization
- Amazon ECR
- automated API testing
- GitHub Actions CI

---

## Future Improvements

Potential production extensions include:

### Streaming

- Multiple Kafka partitions
- Multiple consumer instances
- Amazon MSK
- Schema Registry
- persistent event idempotency
- dead-letter queues
- event replay and recovery

### Machine Learning

- SageMaker Model Registry
- automated model retraining
- model version promotion
- feature-store integration
- model drift monitoring
- data drift monitoring
- prediction monitoring

### Infrastructure

- Amazon EKS deployment
- workload IAM
- Infrastructure as Code
- autoscaling
- centralized logging
- metrics and alerts

### API

- asynchronous inference where appropriate
- request tracing
- authentication
- rate limiting
- model-version routing

---

## Production Considerations

Several prototype simplifications would be hardened in production.

### Event Idempotency

Kafka-compatible systems may deliver messages more than once.

A production consumer would persist processed event IDs or use another idempotency strategy before mutating aircraft state.

### State Recovery

The prototype uses DynamoDB as the durable state store.

A production streaming architecture could additionally use replayable event logs or a dedicated stream-processing framework for more sophisticated state recovery.

### Kafka Scaling

Multiple topic partitions would allow multiple consumer instances to process aircraft events concurrently.

Aircraft tail number would remain the message key to preserve aircraft-specific ordering.

### Model Artifact Management

The small model artifact is committed to the repository for simplicity in the demo.

A production system would typically store and version model artifacts using an artifact store such as Amazon S3 or a model registry.

### AWS Authentication

Static AWS credentials are never embedded into images or source code.

Production workloads should use workload-specific, least-privilege IAM permissions.

---

## What This Project Demonstrates

This project demonstrates practical experience across multiple areas of production ML and backend engineering:

- Python backend development
- REST API design
- machine-learning inference
- ML preprocessing pipelines
- real-time messaging
- Kafka event processing
- stateful stream processing
- NoSQL data modeling
- DynamoDB
- containerization
- Docker
- Amazon ECR
- automated testing
- mocking external services
- CI workflows
- GitHub Actions
- cloud integration
- distributed-system design
- production ML architecture

---

## Summary

AirlineOps AI combines historical airline data with real-time aircraft operational state to provide flight-delay predictions.

The key system flow is:

```text
Historical Flights
      |
      v
XGBoost Model


Aircraft Events
      |
      v
Kafka / Redpanda
      |
      v
Stateful Consumer
      |
      v
DynamoDB
      |
      v
FastAPI
      |
      v
XGBoost
      |
      v
Real-Time Delay Prediction
```

The project demonstrates how a machine-learning model can be integrated into an event-driven backend architecture rather than being treated as an isolated data-science artifact.