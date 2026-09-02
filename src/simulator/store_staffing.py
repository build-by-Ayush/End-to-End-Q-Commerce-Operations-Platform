from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from simulator.orders import (
    demand_multiplier_for_date,
    demand_multiplier_for_hour,
)

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def generate_available_staff(
    scheduled: int,
    availability_rates: list[float],
    weights: list[int],
) -> int:
    """Generate a plausible available headcount for one role/hour."""

    if scheduled <= 0:
        raise ValueError("scheduled staff must be positive.")

    availability_rate = random.choices(
        population=availability_rates,
        weights=weights,
        k=1,
    )[0]

    if scheduled == 1:
        # A one-person shift usually has coverage, with a small
        # probability of a true operational absence.
        return random.choices(
            population=[1, 0],
            weights=[93, 7],
            k=1,
        )[0]

    return min(
        scheduled,
        max(
            1,
            round(scheduled * availability_rate),
        ),
    )


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


def generate_store_staffing(
    stores: list[dict],
    start_datetime: datetime,
    hours: int,
    interval_hours: int = 1,
) -> list[dict]:
    """
    Generate hourly staffing observations for every store.

    Staffing is influenced by the store's baseline capacity.
    Available staff can be lower than scheduled staff to simulate
    breaks, absenteeism, and operational conditions.
    """
    if not stores:
        raise ValueError("Stores cannot be empty.")

    if hours <= 0:
        raise ValueError("hours must be greater than zero.")

    if interval_hours <= 0:
        raise ValueError(
            "interval_hours must be greater than zero."
        )

    if hours % interval_hours != 0:
        raise ValueError(
            "hours must be divisible by interval_hours."
        )

    staffing = []
    snapshot_counter = 1

    for store in stores:
        baseline_capacity = int(store["baseline_capacity"])

        # Convert baseline order/hour capacity into a reasonable
        # staffing level for the simulator.
        base_pickers = max(
            2,
            round(baseline_capacity / 35),
        )

        base_packers = max(
            1,
            round(baseline_capacity / 60),
        )

        for hour_offset in range(
            0,
            hours,
            interval_hours,
        ):
            recorded_at = (
                start_datetime
                + timedelta(hours=hour_offset)
            )

            demand_multiplier = (
                demand_multiplier_for_hour(
                    recorded_at.hour
                )
                * demand_multiplier_for_date(
                    recorded_at
                )
            )

            pickers_scheduled = max(
                1,
                round(base_pickers * demand_multiplier),
            )

            packers_scheduled = max(
                1,
                round(base_packers * demand_multiplier),
            )

            # Availability is normally high, but lower staffing has a
            # direct, probabilistic effect on fulfilment duration.
            pickers_available = generate_available_staff(
                scheduled=pickers_scheduled,
                availability_rates=[1.00, 0.90, 0.75, 0.60],
                weights=[55, 25, 15, 5],
            )

            packers_available = generate_available_staff(
                scheduled=packers_scheduled,
                availability_rates=[1.00, 0.90, 0.75, 0.60],
                weights=[60, 25, 10, 5],
            )

            staffing.append(
                {
                    "staffing_snapshot_id": (
                        f"STAFF-{snapshot_counter:07d}"
                    ),
                    "store_id": store["store_id"],
                    "recorded_at": recorded_at.strftime(
                        TIMESTAMP_FORMAT
                    ),
                    "pickers_scheduled": pickers_scheduled,
                    "pickers_available": pickers_available,
                    "packers_scheduled": packers_scheduled,
                    "packers_available": packers_available,
                }
            )

            snapshot_counter += 1

    return staffing


def save_store_staffing(
    staffing: list[dict],
) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "store_staffing.csv"

    fieldnames = [
        "staffing_snapshot_id",
        "store_id",
        "recorded_at",
        "pickers_scheduled",
        "pickers_available",
        "packers_scheduled",
        "packers_available",
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
        writer.writerows(staffing)

    print(f"Generated {len(staffing)} staffing observations")
    print(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    stores = load_csv("stores.csv")

    start_datetime = datetime(
        2026,
        8,
        15,
        0,
        0,
        0,
    )

    staffing = generate_store_staffing(
        stores=stores,
        start_datetime=start_datetime,
        hours=24,
    )

    save_store_staffing(staffing)
