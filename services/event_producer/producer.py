import json
import random
import time
import uuid

from datetime import datetime, timezone

from confluent_kafka import Producer


BOOTSTRAP_SERVERS = "localhost:9092"

TOPIC = "flight-events"


AIRPORTS = [
    "JFK",
    "BOS",
    "MCO",
    "LAX",
    "BUF",
    "ATL",
]


# Current physical location of each aircraft.
AIRCRAFT = {
    "N101JB": "JFK",
    "N102JB": "BOS",
    "N103JB": "MCO",
    "N104JB": "BUF",
}


producer = Producer(
    {
        "bootstrap.servers": BOOTSTRAP_SERVERS
    }
)


def delivery_report(err, msg):

    if err is not None:
        print(
            f"Delivery failed: {err}"
        )
        return

    print(
        f"Delivered to topic={msg.topic()} "
        f"partition={msg.partition()}"
    )


def create_arrival_event():

    # Pick one aircraft.
    tail_number = random.choice(
        list(AIRCRAFT.keys())
    )

    # Its current physical airport becomes
    # this flight's origin.
    origin = AIRCRAFT[
        tail_number
    ]

    # Pick another airport as destination.
    possible_destinations = [
        airport
        for airport in AIRPORTS
        if airport != origin
    ]

    destination = random.choice(
        possible_destinations
    )

    flight_number = random.randint(
        100,
        999,
    )

    arrival_delay = random.randint(
        -10,
        90,
    )

    event = {
        "event_id": str(
            uuid.uuid4()
        ),

        "event_type":
            "AIRCRAFT_ARRIVED",

        "event_time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "flight_id":
            f"B6{flight_number}",

        "tail_number":
            tail_number,

        "origin":
            origin,

        "destination":
            destination,

        "arrival_delay_minutes":
            arrival_delay,
    }

    # Aircraft has now arrived at the
    # destination, so update its position.
    AIRCRAFT[
        tail_number
    ] = destination

    return event


def main():

    print(
        "Starting airline event producer..."
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:

        while True:

            event = (
                create_arrival_event()
            )

            print(
                "\nPublishing event:"
            )

            print(
                json.dumps(
                    event,
                    indent=2,
                )
            )

            producer.produce(
                topic=TOPIC,

                # Critical:
                # use the aircraft tail number
                # as Kafka message key.
                key=event[
                    "tail_number"
                ],

                value=json.dumps(
                    event
                ),

                callback=delivery_report,
            )

            producer.poll(0)

            time.sleep(3)

    except KeyboardInterrupt:

        print(
            "\nStopping producer..."
        )

    finally:

        producer.flush()


if __name__ == "__main__":
    main()