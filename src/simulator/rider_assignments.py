from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

RESPONSES = [
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
]

REJECTION_REASONS = [
    "TOO_FAR",
    "BUSY",
    "LOW_PAY",
    "OUTSIDE_PREFERRED_ZONE",
    "PERSONAL_REASON",
]


def parse_datetime(value: str) -> datetime:
    return datetime.strptime(
        value,
        TIMESTAMP_FORMAT,
    )


def format_datetime(value: datetime) -> str:
    return value.strftime(
        TIMESTAMP_FORMAT
    )


def generate_assignment_attempts(
    delivery: dict,
    fulfilment: dict,
    store: dict,
    riders: list[dict],
    rider_available_at: dict[str, datetime],
    assignment_counter: int,
    offered_at: datetime,
) -> tuple[
    list[dict],
    str | None,
    datetime | None,
    int,
]:
    """
    Generate rider assignment attempts for one delivery.

    The lifecycle engine owns the timeline.

    This function only answers:
        - Which riders were offered?
        - What did they respond?
        - Who accepted?

    Returns:
        assignments
        accepted_rider_id
        accepted_at
        next_assignment_counter
    """

    active_riders = [
        rider
        for rider in riders
        if rider["status"] == "ACTIVE"
    ]

    available_riders = [
        rider
        for rider in active_riders
        if rider_available_at[
            rider["rider_id"]
        ] <= offered_at
    ]

    matching_riders = [
        rider
        for rider in available_riders
        if rider["home_zone"] == store["zone"]
    ]

    candidate_pool = (
        matching_riders
        if matching_riders
        else available_riders
    )

    if not candidate_pool:
        return (
            [],
            None,
            None,
            assignment_counter,
        )

    candidate_count = min(
        len(candidate_pool),
        random.randint(1, 3),
    )

    candidates = random.sample(
        candidate_pool,
        k=candidate_count,
    )

    assignments = []

    accepted_rider_id: str | None = None
    accepted_at: datetime | None = None

    for candidate in candidates:

        response_roll = random.random()

        if response_roll < 0.70:
            response = "ACCEPTED"

        elif response_roll < 0.90:
            response = "REJECTED"

        else:
            response = "EXPIRED"

        response_time = (
            offered_at
            + timedelta(
                seconds=random.randint(
                    20,
                    90,
                )
            )
        )

        rejection_reason = ""

        responded_at = ""
        expired_at = ""

        if response == "ACCEPTED":
            responded_at = format_datetime(
                response_time
            )

        elif response == "REJECTED":
            responded_at = format_datetime(
                response_time
            )

            rejection_reason = random.choice(
                REJECTION_REASONS
            )

        elif response == "EXPIRED":
            expired_at = format_datetime(
                response_time
            )

        assignments.append(
            {
                "assignment_id": (
                    f"RA-{assignment_counter:07d}"
                ),
                "delivery_id": (
                    delivery["delivery_id"]
                ),
                "rider_id": (
                    candidate["rider_id"]
                ),
                "offered_at": format_datetime(
                    offered_at
                ),
                "responded_at": responded_at,
                "expired_at": expired_at,
                "response": response,
                "rejection_reason": (
                    rejection_reason
                ),
            }
        )

        assignment_counter += 1

        if response == "ACCEPTED":

            accepted_rider_id = (
                candidate["rider_id"]
            )

            accepted_at = response_time

            break

    return (
        assignments,
        accepted_rider_id,
        accepted_at,
        assignment_counter,
    )


def save_assignments(
    assignments: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "rider_assignments.csv"
    )

    fieldnames = [
        "assignment_id",
        "delivery_id",
        "rider_id",
        "offered_at",
        "responded_at",
        "response",
        "rejection_reason",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(assignments)

    print(
        f"Generated {len(assignments)} "
        "rider assignments"
    )

    print(
        f"Dataset saved to: {output_file}"
    )


def save_updated_deliveries(
    deliveries: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "deliveries.csv"
    )

    fieldnames = [
        "delivery_id",
        "fulfilment_unit_id",
        "rider_id",
        "status",
        "rider_arrived_at_store",
        "picked_up_at",
        "delivery_started_at",
        "delivered_at",
        "delivery_distance",
        "traffic_condition",
        "weather_condition",
        "cancelled_at",
        "cancellation_reason",
        "failed_at",
        "failure_reason",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(deliveries)

    print(
        f"Updated {len(deliveries)} "
        "deliveries"
    )

    print(
        f"Dataset saved to: {output_file}"
    )


def load_csv(
    filename: str,
) -> list[dict]:

    dataset_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    input_file = dataset_dir / filename

    if not input_file.exists():
        raise FileNotFoundError(
            f"Required dataset not found: "
            f"{input_file}"
        )

    with input_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


if __name__ == "__main__":

    deliveries = load_csv(
        "deliveries.csv"
    )

    riders = load_csv(
        "riders.csv"
    )

    fulfilment_units = load_csv(
        "fulfilment_units.csv"
    )

    stores = load_csv(
        "stores.csv"
    )

    assignments, updated_deliveries = (
        generate_rider_assignments(
            deliveries=deliveries,
            riders=riders,
            fulfilment_units=fulfilment_units,
            stores=stores,
        )
    )

    save_assignments(
        assignments
    )

    save_updated_deliveries(
        updated_deliveries
    )