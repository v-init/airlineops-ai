import json

import boto3
from confluent_kafka import Consumer, KafkaError


BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "flight-events"

AWS_REGION = "us-east-1"
DYNAMODB_TABLE = "airlineops-aircraft-state"


dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
)

aircraft_table = dynamodb.Table(
    DYNAMODB_TABLE
)

consumer = Consumer(
    {
        "bootstrap.servers": BOOTSTRAP_SERVERS,

        "group.id": "aircraft-state-processor",

        "auto.offset.reset": "earliest",

        # For the prototype, automatic offset commits are fine.
        "enable.auto.commit": True,
    }
)


def update_aircraft_state(event):

    if (
        event.get("event_type")
        != "AIRCRAFT_ARRIVED"
    ):
        return

    state = {
        "tail_number":
            event["tail_number"],

        "current_airport":
            event["destination"],

        "previous_flight_id":
            event["flight_id"],

        "previous_arrival_delay":
            int(
                event[
                    "arrival_delay_minutes"
                ]
            ),

        "last_updated":
            event["event_time"],
    }

    aircraft_table.put_item(
        Item=state
    )

    print(
        "\nPersisted aircraft state "
        "to DynamoDB:"
    )

    print(
        json.dumps(
            state,
            indent=2,
        )
    )


def main():

    consumer.subscribe(
        [TOPIC]
    )

    print(
        "Aircraft state processor started."
    )

    print(
        f"Subscribed to: {TOPIC}"
    )

    print(
        f"DynamoDB table: "
        f"{DYNAMODB_TABLE}"
    )
    
    print(
        "Press Ctrl+C to stop."
    )

    try:

        while True:

            message = consumer.poll(
                timeout=1.0
            )

            if message is None:
                continue

            if message.error():

                if (
                    message.error().code()
                    ==
                    KafkaError._PARTITION_EOF
                ):
                    continue

                print(
                    f"Kafka error: "
                    f"{message.error()}"
                )

                continue

            key = message.key()

            if key is not None:
                key = key.decode(
                    "utf-8"
                )

            event = json.loads(
                message.value().decode(
                    "utf-8"
                )
            )

            print(
                "\nReceived event"
            )

            print(
                f"Partition: "
                f"{message.partition()}"
            )

            print(
                f"Offset: "
                f"{message.offset()}"
            )

            print(
                f"Kafka key: {key}"
            )

            print(
                json.dumps(
                    event,
                    indent=2,
                )
            )

            update_aircraft_state(
                event
            )

    except KeyboardInterrupt:

        print(
            "\nStopping state processor..."
        )

    finally:

        consumer.close()

        print(
            "Consumer closed."
        )


if __name__ == "__main__":
    main()