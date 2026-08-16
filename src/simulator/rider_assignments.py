from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


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
    """Convert a simulator timestamp string to datetime."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def format_datetime(value: datetime) -> str:
    """Convert datetime back to simulator timestamp format."""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def generate_rider_assignments(
    deliveries: list[dict],
    riders: list[dict],
    fulfilment_units: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Generate rider assignment attempts.

    Returns:
        assignments:
            Assignment attempts for each delivery.

        updated_deliveries:
            Deliveries with the final accepted rider_id and status.
    """

    if not deliveries:
        raise ValueError("Deliveries cannot be empty.")

    if not riders:
        raise ValueError("Riders cannot be empty.")

    if not fulfilment_units:
        raise ValueError("Fulfilment units cannot be empty.")

    fulfilments_by_id = {
        fulfilment["fulfilment_unit_id"]: fulfilment
        for fulfilment in fulfilment_units
    }

    # Track the point in time at which each rider becomes available.
    #
    # Example:
    # RID-000001 -> 2026-08-15 10:27:00
    #
    # A rider can only be considered again after this timestamp.
    rider_available_at: dict[str, datetime] = {
        rider["rider_id"]: datetime.min
        for rider in riders
        if rider["status"] == "ACTIVE"
    }

    # Keep the actual rider records for quick lookup.
    riders_by_id = {
        rider["rider_id"]: rider
        for rider in riders
    }

    assignments = []
    updated_deliveries = []

    assignment_counter = 1

    # Process deliveries chronologically so rider availability
    # can be evaluated correctly.
    sorted_deliveries = sorted(
        deliveries,
        key=lambda delivery: parse_datetime(
            fulfilments_by_id[
                delivery["fulfilment_unit_id"]
            ]["assigned_to_store_at"]
        ),
    )

    for delivery in sorted_deliveries:
        fulfilment = fulfilments_by_id.get(
            delivery["fulfilment_unit_id"]
        )

        if fulfilment is None:
            raise ValueError(
                "Fulfilment unit not found: "
                f"{delivery['fulfilment_unit_id']}"
            )

        offered_at = parse_datetime(
            fulfilment["assigned_to_store_at"]
        ) + timedelta(
            minutes=random.randint(1, 5)
        )

        # Find riders who are available at the time of the request.
        available_riders = [
            rider
            for rider_id, rider in riders_by_id.items()
            if rider_available_at[rider_id] <= offered_at
        ]

        # Prefer riders whose home zone matches the fulfilment store's
        # zone. We do not yet have detailed store-distance dispatch logic.
        matching_riders = [
            rider
            for rider in available_riders
            if rider["home_zone"]
            == fulfilment.get("store_zone")
        ]

        candidate_pool = matching_riders or available_riders

        # If no rider is available, the delivery remains unassigned.
        if not candidate_pool:
            updated_delivery = dict(delivery)
            updated_delivery["status"] = "NO_RIDER_AVAILABLE"

            updated_deliveries.append(updated_delivery)
            continue

        # Randomly inspect a small number of riders before acceptance.
        candidate_count = min(
            len(candidate_pool),
            random.randint(1, 3),
        )

        candidates = random.sample(
            candidate_pool,
            k=candidate_count,
        )

        accepted_rider_id = None

        for candidate in candidates:
            response_roll = random.random()

            if response_roll < 0.70:
                response = "ACCEPTED"
            elif response_roll < 0.90:
                response = "REJECTED"
            else:
                response = "EXPIRED"

            responded_at = offered_at + timedelta(
                seconds=random.randint(20, 90)
            )

            rejection_reason = ""

            if response == "REJECTED":
                rejection_reason = random.choice(
                    REJECTION_REASONS
                )

            assignments.append(
                {
                    "assignment_id": (
                        f"RA-{assignment_counter:07d}"
                    ),
                    "delivery_id": delivery["delivery_id"],
                    "rider_id": candidate["rider_id"],
                    "offered_at": format_datetime(
                        offered_at
                    ),
                    "responded_at": format_datetime(
                        responded_at
                    ),
                    "response": response,
                    "rejection_reason": rejection_reason,
                }
            )

            assignment_counter += 1

            if response == "ACCEPTED":
                accepted_rider_id = candidate["rider_id"]

                # The rider becomes unavailable immediately after
                # accepting and remains unavailable for a simulated
                # delivery duration.
                delivery_duration = timedelta(
                    minutes=random.randint(8, 25)
                )

                rider_available_at[
                    candidate["rider_id"]
                ] = responded_at + delivery_duration

                break

            # Rejected/expired riders remain available for other work.

        updated_delivery = dict(delivery)

        if accepted_rider_id is not None:
            updated_delivery["rider_id"] = accepted_rider_id
            updated_delivery["status"] = "ASSIGNED"
        else:
            updated_delivery["status"] = "NO_RIDER_ACCEPTED"

        updated_deliveries.append(updated_delivery)

    return assignments, updated_deliveries


def save_assignments(
    assignments: list[dict],
) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "rider_assignments.csv"

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

    print(f"Generated {len(assignments)} rider assignments")
    print(f"Dataset saved to: {output_file}")


def save_updated_deliveries(
    deliveries: list[dict],
) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "deliveries.csv"

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

    print(f"Updated {len(deliveries)} deliveries")
    print(f"Dataset saved to: {output_file}")


def load_csv(filename: str) -> list[dict]:
    """Load a simulator dataset from src/datasets."""
    dataset_dir = Path(__file__).parent.parent / "datasets"
    input_file = dataset_dir / filename

    if not input_file.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {input_file}"
        )

    with input_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    deliveries = load_csv("deliveries.csv")
    riders = load_csv("riders.csv")
    fulfilment_units = load_csv("fulfilment_units.csv")

    assignments, updated_deliveries = (
        generate_rider_assignments(
            deliveries=deliveries,
            riders=riders,
            fulfilment_units=fulfilment_units,
        )
    )

    save_assignments(assignments)
    save_updated_deliveries(updated_deliveries)