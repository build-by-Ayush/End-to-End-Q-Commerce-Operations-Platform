from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


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
    hours: int = 24,
) -> list[dict]:
    """
    Generate hourly staffing observations for every store.

    Staffing is influenced by the store's baseline capacity.
    Available staff can be lower than scheduled staff to simulate
    breaks, absenteeism, and operational conditions.
    """
    if not stores:
        raise ValueError("Stores cannot be empty.")

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

        for hour_offset in range(hours):
            recorded_at = (
                start_datetime
                + timedelta(hours=hour_offset)
            )

            hour = recorded_at.hour

            # More planned staff during major demand periods.
            if 11 <= hour < 14 or 17 <= hour < 22:
                demand_multiplier = 1.20
            elif 7 <= hour < 11:
                demand_multiplier = 1.05
            else:
                demand_multiplier = 0.80

            pickers_scheduled = max(
                1,
                round(base_pickers * demand_multiplier),
            )

            packers_scheduled = max(
                1,
                round(base_packers * demand_multiplier),
            )

            # Availability is normally high, but occasionally
            # staffing falls below scheduled capacity.
            picker_availability_rate = random.choices(
                population=[
                    1.00,
                    0.90,
                    0.75,
                    0.60,
                ],
                weights=[
                    55,
                    25,
                    15,
                    5,
                ],
                k=1,
            )[0]

            packer_availability_rate = random.choices(
                population=[
                    1.00,
                    0.90,
                    0.75,
                    0.60,
                ],
                weights=[
                    60,
                    25,
                    10,
                    5,
                ],
                k=1,
            )[0]

            pickers_available = min(
                pickers_scheduled,
                max(
                    0,
                    round(
                        pickers_scheduled
                        * picker_availability_rate
                    ),
                ),
            )

            packers_available = min(
                packers_scheduled,
                max(
                    0,
                    round(
                        packers_scheduled
                        * packer_availability_rate
                    ),
                ),
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