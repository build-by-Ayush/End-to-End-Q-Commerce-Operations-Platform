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

    assignments = []
    accepted_rider_id: str | None = None
    accepted_at: datetime | None = None
    attempted_rider_ids: set[str] = set()
    next_offered_at = offered_at
    max_attempts = random.randint(1, 3)

    for _ in range(max_attempts):

        available_riders = [
            rider
            for rider in active_riders
            if (
                rider["rider_id"] not in attempted_rider_ids
                and rider_available_at[
                    rider["rider_id"]
                ] <= next_offered_at
            )
        ]

        # Without rider-location telemetry, home zone is the only
        # credible proximity proxy. Do not fall back to any rider in
        # the city and then claim they arrive in one to five minutes.
        candidate_pool = [
            rider
            for rider in available_riders
            if rider["home_zone"] == store["zone"]
        ]

        if not candidate_pool:
            break

        candidate = random.choice(candidate_pool)
        attempted_rider_ids.add(candidate["rider_id"])

        response_roll = random.random()

        if response_roll < 0.70:
            response = "ACCEPTED"

        elif response_roll < 0.90:
            response = "REJECTED"

        else:
            response = "EXPIRED"

        response_time = (
            next_offered_at
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
                    next_offered_at
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

        # A rejected or expired offer is resolved before the next
        # rider is contacted, preserving a genuine attempt sequence.
        next_offered_at = response_time + timedelta(
            seconds=random.randint(10, 30)
        )

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
        "expired_at",
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
    raise SystemExit(
        "Run simulator.run_simulation for lifecycle-aware "
        "rider assignment generation."
    )
