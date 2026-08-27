from __future__ import annotations

import csv
import random
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent

CLEAN_DIR = BASE_DIR / "datasets"
DIRTY_DIR = BASE_DIR / "datasets_dirty"

RANDOM_SEED = 2026

# Approximate percentage of eligible values/rows affected.
TEXT_CORRUPTION_RATE = 0.05
TIMESTAMP_CORRUPTION_RATE = 0.03
NULL_CORRUPTION_RATE = 0.02
DUPLICATE_RATE = 0.02


DATASET_FILES = [
    "customers.csv",
    "stores.csv",
    "riders.csv",
    "orders.csv",
    "fulfilment_units.csv",
    "order_items.csv",
    "deliveries.csv",
    "rider_assignments.csv",
    "operational_events.csv",
    "store_staffing.csv",
]


# ---------------------------------------------------------
# Fields used for different corruption types
# ---------------------------------------------------------

TEXT_FIELDS = {
    "stores.csv": [
        "store_name",
        "zone",
    ],
    "riders.csv": [
        "vehicle_type",
        "home_zone",
        "status",
    ],
    "orders.csv": [
        "delivery_zone",
        "status",
        "cancellation_reason",
        "failure_reason",
    ],
    "fulfilment_units.csv": [
        "status",
        "cancellation_reason",
        "failure_reason",
    ],
    "order_items.csv": [
        "product_id",
    ],
    "deliveries.csv": [
        "status",
        "traffic_condition",
        "weather_condition",
        "cancellation_reason",
        "failure_reason",
    ],
    "rider_assignments.csv": [
        "response",
        "rejection_reason",
    ],
    "operational_events.csv": [
        "event_type",
        "reason",
    ],
    "store_staffing.csv": [],
}


TIMESTAMP_FIELDS = {
    "orders.csv": [
        "created_at",
        "payment_success_at",
        "cancelled_at",
    ],
    "fulfilment_units.csv": [
        "assigned_to_store_at",
        "picking_started_at",
        "picking_completed_at",
        "packing_started_at",
        "packing_completed_at",
        "cancelled_at",
        "failed_at",
        "completed_at",
    ],
    "deliveries.csv": [
        "rider_arrived_at_store",
        "picked_up_at",
        "delivery_started_at",
        "delivered_at",
        "cancelled_at",
        "failed_at",
    ],
    "rider_assignments.csv": [
        "offered_at",
        "responded_at",
        "expired_at",
    ],
    "operational_events.csv": [
        "occurred_at",
    ],
    "store_staffing.csv": [
        "recorded_at",
    ],
}


NULLABLE_FIELDS = {
    "stores.csv": [
        "closed_at",
    ],
    "riders.csv": [
        "deactivated_at",
    ],
    "orders.csv": [
        "cancelled_at",
        "cancellation_reason",
        "failure_reason",
    ],
    "fulfilment_units.csv": [
        "cancelled_at",
        "cancellation_reason",
        "failed_at",
        "failure_reason",
        "completed_at",
    ],
    "deliveries.csv": [
        "cancelled_at",
        "cancellation_reason",
        "failed_at",
        "failure_reason",
    ],
    "rider_assignments.csv": [
        "responded_at",
        "expired_at",
        "rejection_reason",
    ],
    "operational_events.csv": [
        "reason",
    ],
}


TIMESTAMP_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
]


def corrupt_text(
    value: str,
    rng: random.Random,
) -> str:
    """
    Apply one technical text-quality problem.
    """

    if not value:
        return value

    corruption_type = rng.choice(
        [
            "leading_trailing_space",
            "lowercase",
            "uppercase",
            "special_character",
        ]
    )

    if corruption_type == (
        "leading_trailing_space"
    ):
        return f"  {value} "

    if corruption_type == "lowercase":
        return value.lower()

    if corruption_type == "uppercase":
        return value.upper()

    return f"{value}#"


def corrupt_timestamp(
    value: str,
    rng: random.Random,
) -> str:
    """
    Convert a clean timestamp into another
    valid-looking textual representation.
    """

    if not value:
        return value

    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S",
        )

    except ValueError:
        return value

    timestamp_format = rng.choice(
        TIMESTAMP_FORMATS
    )

    return parsed.strftime(
        timestamp_format
    )


def corrupt_nullable_value(
    value: str,
    rng: random.Random,
) -> str:
    """
    Turn an existing blank value into one of several
    inconsistent source-system null representations.
    """

    if value:
        return value

    return rng.choice(
        [
            "",
            " ",
            "NULL",
        ]
    )


def corrupt_row(
    filename: str,
    row: dict[str, str],
    rng: random.Random,
) -> dict[str, str]:
    """
    Apply all configured corruption rules to one row.
    """

    text_fields = TEXT_FIELDS.get(
        filename,
        [],
    )

    timestamp_fields = TIMESTAMP_FIELDS.get(
        filename,
        [],
    )

    nullable_fields = NULLABLE_FIELDS.get(
        filename,
        [],
    )

    # Work on only the current row.
    dirty_row = dict(row)

    # -----------------------------------------------------
    # Text corruption
    # -----------------------------------------------------

    for field in text_fields:

        value = dirty_row.get(
            field,
            "",
        )

        if (
            value
            and rng.random()
            < TEXT_CORRUPTION_RATE
        ):
            dirty_row[field] = corrupt_text(
                value,
                rng,
            )

    # -----------------------------------------------------
    # Timestamp-format corruption
    # -----------------------------------------------------

    for field in timestamp_fields:

        value = dirty_row.get(
            field,
            "",
        )

        if (
            value
            and rng.random()
            < TIMESTAMP_CORRUPTION_RATE
        ):
            dirty_row[field] = corrupt_timestamp(
                value,
                rng,
            )

    # -----------------------------------------------------
    # NULL / blank inconsistency
    # -----------------------------------------------------

    for field in nullable_fields:

        value = dirty_row.get(
            field,
            "",
        )

        if (
            not value
            and rng.random()
            < NULL_CORRUPTION_RATE
        ):
            dirty_row[field] = (
                corrupt_nullable_value(
                    value,
                    rng,
                )
            )

    return dirty_row


def process_dataset(
    input_file: Path,
    output_file: Path,
    filename: str,
    rng: random.Random,
) -> tuple[int, int]:
    """
    Stream one clean CSV into one dirty CSV.

    Returns:
        clean_row_count
        dirty_row_count
    """

    clean_count = 0
    dirty_count = 0

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with (
        input_file.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as source_file,
        output_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as target_file,
    ):

        reader = csv.DictReader(
            source_file
        )

        fieldnames = reader.fieldnames or []

        if not fieldnames:
            raise ValueError(
                f"No CSV columns found in {input_file}"
            )

        writer = csv.DictWriter(
            target_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in reader:

            clean_count += 1

            dirty_row = corrupt_row(
                filename=filename,
                row=row,
                rng=rng,
            )

            writer.writerow(
                dirty_row
            )

            dirty_count += 1

            # -------------------------------------------------
            # Duplicate injection
            #
            # Instead of selecting duplicate rows from the
            # entire dataset in memory, probabilistically
            # duplicate individual rows while streaming.
            # -------------------------------------------------

            if (
                rng.random()
                < DUPLICATE_RATE
            ):
                writer.writerow(
                    dirty_row
                )

                dirty_count += 1

    return (
        clean_count,
        dirty_count,
    )


def inject_dirty_data() -> None:
    """
    Create dirty copies of the clean simulator datasets
    without loading entire datasets into memory.
    """

    if not CLEAN_DIR.exists():

        raise FileNotFoundError(
            f"Clean dataset directory not found: "
            f"{CLEAN_DIR}"
        )

    DIRTY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rng = random.Random(
        RANDOM_SEED
    )

    print("=" * 60)
    print("DIRTY DATA INJECTION")
    print("=" * 60)

    total_clean_rows = 0
    total_dirty_rows = 0

    for filename in DATASET_FILES:

        clean_file = (
            CLEAN_DIR / filename
        )

        dirty_file = (
            DIRTY_DIR / filename
        )

        if not clean_file.exists():

            raise FileNotFoundError(
                f"Clean dataset not found: "
                f"{clean_file}"
            )

        clean_count, dirty_count = (
            process_dataset(
                input_file=clean_file,
                output_file=dirty_file,
                filename=filename,
                rng=rng,
            )
        )

        total_clean_rows += clean_count
        total_dirty_rows += dirty_count

        print(
            f"{filename:<30}"
            f"{clean_count:>10,} clean  →  "
            f"{dirty_count:>10,} dirty"
        )

    print(
        f"\nTotal clean rows: "
        f"{total_clean_rows:,}"
    )

    print(
        f"Total dirty rows: "
        f"{total_dirty_rows:,}"
    )

    print(
        "\nDirty datasets saved to:"
    )

    print(DIRTY_DIR)

    print("\n" + "=" * 60)
    print(
        "DIRTY DATA INJECTION COMPLETE"
    )
    print("=" * 60)


if __name__ == "__main__":
    inject_dirty_data()