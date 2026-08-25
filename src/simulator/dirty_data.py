from __future__ import annotations

import csv
import random
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


# These are optional/contextual fields where a blank value
# is already semantically possible.
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


def load_csv(
    file_path: Path,
) -> tuple[list[dict], list[str]]:
    """Load a CSV file and preserve its column order."""

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        rows = list(reader)
        fieldnames = reader.fieldnames or []

    return rows, fieldnames


def save_csv(
    file_path: Path,
    rows: list[dict],
    fieldnames: list[str],
) -> None:
    """Save rows to CSV."""

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def corrupt_text(
    value: str,
    rng: random.Random,
) -> str:
    """Apply one simple textual-quality problem."""

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
    """Convert a clean timestamp into another valid-looking format."""

    if not value:
        return value

    from datetime import datetime

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
    """Introduce inconsistent null representation."""

    if value:
        return value

    return rng.choice(
        [
            "",
            " ",
            "NULL",
        ]
    )


def inject_row_duplicates(
    rows: list[dict],
    rng: random.Random,
) -> list[dict]:
    """
    Duplicate a small number of complete records.

    This simulates duplicate ingestion/source delivery.
    """

    if not rows:
        return rows

    duplicate_count = max(
        1,
        int(
            len(rows)
            * DUPLICATE_RATE
        ),
    )

    selected_rows = rng.sample(
        rows,
        k=min(
            duplicate_count,
            len(rows),
        ),
    )

    result = list(rows)

    for row in selected_rows:
        result.append(dict(row))

    rng.shuffle(result)

    return result


def corrupt_dataset(
    filename: str,
    rows: list[dict],
    rng: random.Random,
) -> list[dict]:
    """Apply controlled technical corruption to one dataset."""

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

    dirty_rows = [
        dict(row)
        for row in rows
    ]

    for row in dirty_rows:

        # -----------------------------------------------------
        # Text corruption
        # -----------------------------------------------------

        for field in text_fields:

            value = row.get(field, "")

            if (
                value
                and rng.random()
                < TEXT_CORRUPTION_RATE
            ):
                row[field] = corrupt_text(
                    value,
                    rng,
                )

        # -----------------------------------------------------
        # Timestamp-format corruption
        # -----------------------------------------------------

        for field in timestamp_fields:

            value = row.get(field, "")

            if (
                value
                and rng.random()
                < TIMESTAMP_CORRUPTION_RATE
            ):
                row[field] = corrupt_timestamp(
                    value,
                    rng,
                )

        # -----------------------------------------------------
        # NULL/blank inconsistency
        # -----------------------------------------------------

        for field in nullable_fields:

            value = row.get(field, "")

            if (
                not value
                and rng.random()
                < NULL_CORRUPTION_RATE
            ):
                row[field] = corrupt_nullable_value(
                    value,
                    rng,
                )

    # ---------------------------------------------------------
    # Duplicate records
    # ---------------------------------------------------------

    return inject_row_duplicates(
        dirty_rows,
        rng,
    )


def inject_dirty_data() -> None:
    """Create dirty copies of the clean simulator datasets."""

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

    for filename in DATASET_FILES:

        clean_file = (
            CLEAN_DIR / filename
        )

        if not clean_file.exists():
            raise FileNotFoundError(
                f"Clean dataset not found: "
                f"{clean_file}"
            )

        rows, fieldnames = load_csv(
            clean_file
        )

        dirty_rows = corrupt_dataset(
            filename=filename,
            rows=rows,
            rng=rng,
        )

        dirty_file = (
            DIRTY_DIR / filename
        )

        save_csv(
            dirty_file,
            dirty_rows,
            fieldnames,
        )

        print(
            f"{filename:<30}"
            f"{len(rows):>7} clean  →  "
            f"{len(dirty_rows):>7} dirty"
        )

    print("\nDirty datasets saved to:")
    print(DIRTY_DIR)

    print("\n" + "=" * 60)
    print("DIRTY DATA INJECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    inject_dirty_data()