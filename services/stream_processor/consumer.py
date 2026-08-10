import json

from confluent_kafka import Consumer, KafkaError


BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "flight-events"


consumer = Consumer(
    {
        "bootstrap.servers": BOOTSTRAP_SERVERS,

        "group.id": "aircraft-state-processor",

        "auto.offset.reset": "earliest",

        # For the prototype, automatic offset commits are fine.
        "enable.auto.commit": True,
    }
)


# Local in-memory state for Day 1.
#
# Tomorrow we will replace this
# with DynamoDB.
aircraft_state = {}


def update_aircraft_state(event):

    event_type = event.get(
        "event_type"
    )

    if event_type != "AIRCRAFT_ARRIVED":
        return

    tail_number = event[
        "tail_number"
    ]

    new_state = {
        "tail_number":
            tail_number,

        "current_airport":
            event[
                "destination"
            ],

        "previous_flight_id":
            event[
                "flight_id"
            ],

        "previous_arrival_delay":
            event[
                "arrival_delay_minutes"
            ],

        "last_updated":
            event[
                "event_time"
            ],
    }

    aircraft_state[
        tail_number
    ] = new_state

    print(
        "\n------------------------------"
    )

    print(
        f"Updated aircraft: "
        f"{tail_number}"
    )

    print(
        json.dumps(
            new_state,
            indent=2,
        )
    )

    print(
        f"\nTotal aircraft tracked: "
        f"{len(aircraft_state)}"
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