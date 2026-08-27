from __future__ import annotations

import csv
import random
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from pathlib import Path

from simulator.time_utils import (
    format_timestamp,
    parse_timestamp,
)

from simulator.rider_assignments import (
    generate_assignment_attempts,
)


FULFILMENT_CANCELLATION_RATE = 0.03
FULFILMENT_FAILURE_RATE = 0.02

TIMESTAMP_OFFSET_MIN_SECONDS = 15
TIMESTAMP_OFFSET_MAX_SECONDS = 90


def load_csv(filename: str) -> list[dict]:
    """Load a simulator dataset from src/datasets."""

    dataset_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

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
        return list(
            csv.DictReader(file)
        )


def generate_picking_duration(
    item_count: int,
    pickers_available: int,
    pickers_scheduled: int,
) -> timedelta:
    """
    Generate picking duration using basket complexity
    and available picker capacity.
    """

    if item_count <= 0:
        raise ValueError(
            "item_count must be greater than zero."
        )

    if pickers_scheduled <= 0:
        raise ValueError(
            "pickers_scheduled must be greater than zero."
        )

    base_seconds = 90

    per_item_seconds = random.randint(
        20,
        40,
    )

    random_variation_seconds = random.randint(
        0,
        120,
    )

    normal_seconds = (
        base_seconds
        + item_count * per_item_seconds
        + random_variation_seconds
    )

    staffing_ratio = (
        pickers_available
        / pickers_scheduled
    )

    if staffing_ratio < 0.50:
        staffing_multiplier = 1.35

    elif staffing_ratio < 0.75:
        staffing_multiplier = 1.15

    else:
        staffing_multiplier = 1.00

    total_seconds = (
        normal_seconds
        * staffing_multiplier
    )

    return timedelta(
        seconds=int(total_seconds)
    )


def generate_packing_duration(
    packers_available: int,
    packers_scheduled: int,
) -> timedelta:
    """
    Generate packing duration using packer availability.
    """

    if packers_scheduled <= 0:
        raise ValueError(
            "packers_scheduled must be greater than zero."
        )

    base_seconds = random.randint(
        60,
        150,
    )

    staffing_ratio = (
        packers_available
        / packers_scheduled
    )

    if staffing_ratio < 0.50:
        staffing_multiplier = 1.30

    elif staffing_ratio < 0.75:
        staffing_multiplier = 1.15

    else:
        staffing_multiplier = 1.00

    total_seconds = (
        base_seconds
        * staffing_multiplier
    )

    return timedelta(
        seconds=int(total_seconds)
    )


def choose_fulfilment_outcome() -> str:
    """
    Decide whether a fulfilment follows the normal lifecycle.

    NORMAL is overwhelmingly likely in the clean baseline.
    """

    roll = random.random()

    if roll < FULFILMENT_CANCELLATION_RATE:
        return "CANCELLED"

    if roll < (
        FULFILMENT_CANCELLATION_RATE
        + FULFILMENT_FAILURE_RATE
    ):
        return "FAILED"

    return "NORMAL"


def build_staffing_index(
    store_staffing: list[dict],
) -> dict[
    str,
    tuple[
        list[datetime],
        list[dict],
    ],
]:
    """
    Build a chronological staffing index for each store.

    This is created once before lifecycle processing so that
    staffing lookups are O(log n) instead of repeatedly scanning
    the entire staffing dataset.
    """

    grouped: dict[
        str,
        list[tuple[datetime, dict]],
    ] = {}

    for row in store_staffing:

        store_id = row["store_id"]

        recorded_at = parse_timestamp(
            row["recorded_at"]
        )

        grouped.setdefault(
            store_id,
            [],
        ).append(
            (
                recorded_at,
                row,
            )
        )

    staffing_index: dict[
        str,
        tuple[
            list[datetime],
            list[dict],
        ],
    ] = {}

    for store_id, observations in grouped.items():

        observations.sort(
            key=lambda item: item[0]
        )

        timestamps = [
            observation[0]
            for observation in observations
        ]

        rows = [
            observation[1]
            for observation in observations
        ]

        staffing_index[store_id] = (
            timestamps,
            rows,
        )

    return staffing_index


def get_staffing_at_time(
    store_id: str,
    timestamp: datetime,
    staffing_index: dict[
        str,
        tuple[
            list[datetime],
            list[dict],
        ],
    ],
) -> dict:
    """
    Return the latest staffing observation at or before
    the requested timestamp.

    If the requested timestamp occurs before the first
    observation, use the earliest observation.
    """

    indexed_data = staffing_index.get(
        store_id
    )

    if indexed_data is None:
        raise ValueError(
            f"No staffing observations found for store "
            f"{store_id}"
        )

    timestamps, rows = indexed_data

    position = bisect_right(
        timestamps,
        timestamp,
    ) - 1

    if position < 0:
        position = 0

    return rows[position]

def generate_transit_duration(
    distance_km: float,
    traffic_condition: str,
    weather_condition: str,
) -> timedelta:
    """
    Generate last-mile transit duration.

    Distance establishes the baseline.
    Traffic and weather modify it.
    Random variation keeps the relationship probabilistic.
    """

    if distance_km <= 0:
        raise ValueError(
            "distance_km must be greater than zero."
        )

    average_speed_kmh = random.uniform(
        20,
        25,
    )

    base_minutes = (
        distance_km
        / average_speed_kmh
        * 60
    )

    traffic_multiplier = {
        "LOW": 0.90,
        "MODERATE": 1.00,
        "HIGH": 1.20,
        "SEVERE": 1.40,
    }.get(
        traffic_condition,
        1.00,
    )

    weather_multiplier = {
        "CLEAR": 1.00,
        "CLOUDY": 1.02,
        "RAIN": 1.15,
    }.get(
        weather_condition,
        1.00,
    )

    random_variation_minutes = random.uniform(
        0.5,
        1.5,
    )

    total_minutes = (
        base_minutes
        * traffic_multiplier
        * weather_multiplier
        + random_variation_minutes
    )

    return timedelta(
        minutes=total_minutes
    )


def build_workload_index(
    fulfilment_units: list[dict],
) -> dict[
    str,
    list[datetime],
]:
    """
    Build a sorted list of fulfilment assignment timestamps
    for each store.

    This allows workload pressure to be calculated using
    binary searches instead of scanning every fulfilment.
    """

    workload_index: dict[
        str,
        list[datetime],
    ] = {}

    for fulfilment in fulfilment_units:

        store_id = fulfilment[
            "store_id"
        ]

        assigned_at = parse_timestamp(
            fulfilment[
                "assigned_to_store_at"
            ]
        )

        workload_index.setdefault(
            store_id,
            [],
        ).append(assigned_at)

    for timestamps in workload_index.values():
        timestamps.sort()

    return workload_index


def calculate_store_workload_pressure(
    store_id: str,
    assigned_at: datetime,
    stores_by_id: dict[str, dict],
    workload_index: dict[
        str,
        list[datetime],
    ],
) -> float:
    """
    Calculate store workload pressure using a pre-built
    timestamp index.

    Counts fulfilments assigned to the same store within
    +/- 30 minutes of the current assignment time.
    """

    store = stores_by_id.get(
        store_id
    )

    if store is None:
        raise ValueError(
            f"Store not found: {store_id}"
        )

    baseline_capacity = float(
        store["baseline_capacity"]
    )

    if baseline_capacity <= 0:
        raise ValueError(
            f"Invalid baseline capacity for "
            f"store {store_id}"
        )

    timestamps = workload_index.get(
        store_id,
        [],
    )

    if not timestamps:
        return 0.0

    window_start = (
        assigned_at
        - timedelta(minutes=30)
    )

    window_end = (
        assigned_at
        + timedelta(minutes=30)
    )

    left_position = bisect_left(
        timestamps,
        window_start,
    )

    right_position = bisect_right(
        timestamps,
        window_end,
    )

    nearby_workload = (
        right_position
        - left_position
    )

    capacity_threshold = max(
        1.0,
        baseline_capacity / 4,
    )

    pressure_ratio = (
        nearby_workload
        / capacity_threshold
    )

    return min(
        pressure_ratio,
        1.0,
    )

def generate_operational_events(
    orders: list[dict],
    fulfilment_units: list[dict],
    order_items: list[dict],
    deliveries: list[dict],
    riders: list[dict],
    stores: list[dict],
    store_staffing: list[dict],
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
    list[dict],
    list[dict],
]:
    """
    Generate the operational lifecycle.

    Returns:
        events
        updated orders
        updated fulfilment units
        updated deliveries
        updated assignments
    """

    orders_by_id = {
        order["order_id"]: order
        for order in orders
    }

    stores_by_id = {
        store["store_id"]: store
        for store in stores
    }

    staffing_index = build_staffing_index(
        store_staffing
    )

    workload_index = build_workload_index(
        fulfilment_units
    )

    items_by_fulfilment: dict[str, int] = {}

    for item in order_items:
        fulfilment_id = item["fulfilment_unit_id"]

        items_by_fulfilment[fulfilment_id] = (
            items_by_fulfilment.get(
                fulfilment_id,
                0,
            )
            + 1
        )

    events: list[dict] = []

    updated_orders = [
        dict(order)
        for order in orders
    ]

    updated_fulfilments = [
        dict(fulfilment)
        for fulfilment in fulfilment_units
    ]

    updated_deliveries = [
        dict(delivery)
        for delivery in deliveries
    ]

    deliveries_by_fulfilment = {
        delivery["fulfilment_unit_id"]: delivery
        for delivery in updated_deliveries
    }

    # Rider assignments are now generated inside the
    # lifecycle engine rather than passed in from outside.
    updated_assignments: list[dict] = []

    # Tracks when each rider becomes available again.
    rider_available_at: dict[str, datetime] = {
        rider["rider_id"]: datetime.min
        for rider in riders
        if rider["status"] == "ACTIVE"
    }

    assignment_counter = 1

    event_counter = 1

    def add_event(
        event_type: str,
        occurred_at: datetime,
        order_id: str | None = None,
        fulfilment_unit_id: str | None = None,
        delivery_id: str | None = None,
        store_id: str | None = None,
        rider_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        nonlocal event_counter

        event = {
            "event_id": (
                f"EVT-{event_counter:07d}"
            ),
            "event_type": event_type,
            "occurred_at": format_timestamp(
                occurred_at
            ),
            "order_id": order_id or "",
            "fulfilment_unit_id": (
                fulfilment_unit_id or ""
            ),
            "delivery_id": (
                delivery_id or ""
            ),
            "store_id": store_id or "",
            "rider_id": rider_id or "",
            "reason": reason or "",
        }

        events.append(event)

        event_counter += 1

    # ---------------------------------------------------------
    # Order-level events
    # ---------------------------------------------------------

    for order in updated_orders:

        order_id = order["order_id"]

        created_at = parse_timestamp(
            order["created_at"]
        )

        payment_success_at = parse_timestamp(
            order["payment_success_at"]
        )

        add_event(
            event_type="ORDER_CREATED",
            occurred_at=created_at,
            order_id=order_id,
        )

        add_event(
            event_type="PAYMENT_SUCCESS",
            occurred_at=payment_success_at,
            order_id=order_id,
        )

    # ---------------------------------------------------------
    # Fulfilment and delivery lifecycle
    # ---------------------------------------------------------

    for fulfilment in updated_fulfilments:

        fulfilment_id = (
            fulfilment["fulfilment_unit_id"]
        )

        order_id = fulfilment["order_id"]
        store_id = fulfilment["store_id"]

        order = orders_by_id.get(order_id)

        if order is None:
            raise ValueError(
                f"Order not found: {order_id}"
            )

        delivery = deliveries_by_fulfilment.get(
            fulfilment_id
        )

        if delivery is None:
            raise ValueError(
                "Delivery not found for fulfilment "
                f"{fulfilment_id}"
            )

        assigned_to_store_at = parse_timestamp(
            fulfilment[
                "assigned_to_store_at"
            ]
        )

        payment_success_at = parse_timestamp(
            order["payment_success_at"]
        )

        # -----------------------------------------------------
        # STORE ASSIGNMENT
        # -----------------------------------------------------

        # Protect against malformed ordering.
        assigned_to_store_at = max(
            assigned_to_store_at,
            payment_success_at
            + timedelta(seconds=30),
        )

        add_event(
            event_type="STORE_ASSIGNED",
            occurred_at=assigned_to_store_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            store_id=store_id,
        )

        fulfilment["status"] = "PICKING"

        # -----------------------------------------------------
        # Decide the fulfilment outcome
        # -----------------------------------------------------

        outcome = choose_fulfilment_outcome()

        store_pressure = calculate_store_workload_pressure(
            store_id=store_id,
            assigned_at=assigned_to_store_at,
            stores_by_id=stores_by_id,
            workload_index=workload_index,
        )

        base_wait_seconds = random.randint(
            60,
            180,
        )

        pressure_delay_seconds = int(
            store_pressure * random.randint(
                30,
                120,
            )
        )

        picking_started_at = (
            assigned_to_store_at
            + timedelta(
                seconds=(
                    base_wait_seconds
                    + pressure_delay_seconds
                )
            )
        )

        staffing = get_staffing_at_time(
            store_id=store_id,
            timestamp=picking_started_at,
            staffing_index=staffing_index,
        )

        pickers_available = int(
            staffing["pickers_available"]
        )

        pickers_scheduled = int(
            staffing["pickers_scheduled"]
        )

        packers_available = int(
            staffing["packers_available"]
        )

        packers_scheduled = int(
            staffing["packers_scheduled"]
        )

        add_event(
            event_type="PICKING_STARTED",
            occurred_at=picking_started_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            store_id=store_id,
        )

        fulfilment[
            "picking_started_at"
        ] = format_timestamp(
            picking_started_at
        )

        # -----------------------------------------------------
        # Picking
        # -----------------------------------------------------

        item_count = items_by_fulfilment.get(
            fulfilment_id,
            0,
        )

        if item_count <= 0:
            raise ValueError(
                "No order items found for fulfilment "
                f"{fulfilment_id}"
            )

        picking_completed_at = (
            picking_started_at
            + generate_picking_duration(
                item_count=item_count,
                pickers_available=pickers_available,
                pickers_scheduled=pickers_scheduled,
            )
        )

        add_event(
            event_type="PICKING_COMPLETED",
            occurred_at=picking_completed_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            store_id=store_id,
        )

        fulfilment[
            "picking_completed_at"
        ] = format_timestamp(
            picking_completed_at
        )

        # -----------------------------------------------------
        # Cancellation after picking
        # -----------------------------------------------------

        if outcome == "CANCELLED":

            cancellation_time = (
                picking_completed_at
                + timedelta(
                    seconds=random.randint(
                        30,
                        120,
                    )
                )
            )

            cancellation_reason = random.choice(
                [
                    "CUSTOMER_REQUEST",
                    "STORE_ISSUE",
                    "ITEM_UNAVAILABLE",
                ]
            )

            add_event(
                event_type="FULFILMENT_CANCELLED",
                occurred_at=cancellation_time,
                order_id=order_id,
                fulfilment_unit_id=fulfilment_id,
                store_id=store_id,
                reason=cancellation_reason,
            )

            fulfilment["status"] = (
                "CANCELLED"
            )

            fulfilment["cancelled_at"] = (
                format_timestamp(
                    cancellation_time
                )
            )

            fulfilment[
                "cancellation_reason"
            ] = cancellation_reason

            delivery["status"] = "CANCELLED"

            delivery["cancelled_at"] = (
                format_timestamp(
                    cancellation_time
                )
            )

            delivery[
                "cancellation_reason"
            ] = cancellation_reason

            continue

        # -----------------------------------------------------
        # Packing
        # -----------------------------------------------------

        fulfilment["status"] = "PACKING"

        packing_started_at = (
            picking_completed_at
            + timedelta(
                seconds=random.randint(
                    15,
                    45,
                )
            )
        )

        add_event(
            event_type="PACKING_STARTED",
            occurred_at=packing_started_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            store_id=store_id,
        )

        fulfilment[
            "packing_started_at"
        ] = format_timestamp(
            packing_started_at
        )

        packing_completed_at = (
            packing_started_at
            + generate_packing_duration(
                packers_available=packers_available,
                packers_scheduled=packers_scheduled,
            )
        )

        add_event(
            event_type="PACKING_COMPLETED",
            occurred_at=packing_completed_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            store_id=store_id,
        )

        fulfilment[
            "packing_completed_at"
        ] = format_timestamp(
            packing_completed_at
        )

        # -----------------------------------------------------
        # Failure after packing
        # -----------------------------------------------------

        if outcome == "FAILED":

            failure_time = (
                packing_completed_at
                + timedelta(
                    seconds=random.randint(
                        30,
                        120,
                    )
                )
            )

            failure_reason = random.choice(
                [
                    "STORE_OPERATIONAL_FAILURE",
                    "ITEM_UNAVAILABLE",
                    "FULFILMENT_SYSTEM_ERROR",
                ]
            )

            add_event(
                event_type="FULFILMENT_FAILED",
                occurred_at=failure_time,
                order_id=order_id,
                fulfilment_unit_id=fulfilment_id,
                store_id=store_id,
                reason=failure_reason,
            )

            fulfilment["status"] = "FAILED"

            fulfilment["failed_at"] = (
                format_timestamp(
                    failure_time
                )
            )

            fulfilment[
                "failure_reason"
            ] = failure_reason

            delivery["status"] = "FAILED"

            delivery["failed_at"] = (
                format_timestamp(
                    failure_time
                )
            )

            delivery[
                "failure_reason"
            ] = failure_reason

            continue

        # -----------------------------------------------------
        # Delivery / rider assignment
        # -----------------------------------------------------

        delivery_id = delivery[
            "delivery_id"
        ]

        # The delivery request is created before rider acceptance.
        # Rider assignment now happens here, at the correct
        # point in the operational lifecycle.
        assignment_offered_at = (
            packing_completed_at
            + timedelta(
                seconds=random.randint(
                    30,
                    120,
                )
            )
        )

        store = stores_by_id.get(
            store_id
        )

        if store is None:
            raise ValueError(
                f"Store not found: {store_id}"
            )

        (
            assignment_attempts,
            accepted_rider_id,
            accepted_at,
            assignment_counter,
        ) = generate_assignment_attempts(
            delivery=delivery,
            fulfilment=fulfilment,
            store=store,
            riders=riders,
            rider_available_at=rider_available_at,
            assignment_counter=assignment_counter,
            offered_at=assignment_offered_at,
        )

        updated_assignments.extend(
            assignment_attempts
        )

        # -----------------------------------------------------
        # No rider accepted
        # -----------------------------------------------------

        if accepted_rider_id is None:

            failure_time = (
                assignment_offered_at
                + timedelta(
                    minutes=random.randint(
                        2,
                        5,
                    )
                )
            )

            add_event(
                event_type="DELIVERY_FAILED",
                occurred_at=failure_time,
                order_id=order_id,
                fulfilment_unit_id=fulfilment_id,
                delivery_id=delivery_id,
                store_id=store_id,
                reason="NO_RIDER_ACCEPTED",
            )

            fulfilment["status"] = "FAILED"

            fulfilment["failed_at"] = (
                format_timestamp(
                    failure_time
                )
            )

            fulfilment[
                "failure_reason"
            ] = "NO_RIDER_ACCEPTED"

            delivery["status"] = "FAILED"

            delivery["failed_at"] = (
                format_timestamp(
                    failure_time
                )
            )

            delivery[
                "failure_reason"
            ] = "NO_RIDER_ACCEPTED"

            continue

        # -----------------------------------------------------
        # Rider accepted
        # -----------------------------------------------------

        rider_id = accepted_rider_id

        rider_assigned_at = accepted_at

        add_event(
            event_type="RIDER_ASSIGNED",
            occurred_at=rider_assigned_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            delivery_id=delivery_id,
            store_id=store_id,
            rider_id=rider_id,
        )

        fulfilment["status"] = (
            "READY_FOR_PICKUP"
        )

        delivery["status"] = "ASSIGNED"

        delivery["rider_id"] = rider_id

                # -----------------------------------------------------
        # Rider arrival
        # -----------------------------------------------------

        rider_arrived_at_store = (
            rider_assigned_at
            + timedelta(
                minutes=random.randint(
                    1,
                    5,
                )
            )
        )

        add_event(
            event_type="RIDER_ARRIVED_AT_STORE",
            occurred_at=rider_arrived_at_store,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            delivery_id=delivery_id,
            store_id=store_id,
            rider_id=rider_id,
        )

        delivery[
            "rider_arrived_at_store"
        ] = format_timestamp(
            rider_arrived_at_store
        )

        # -----------------------------------------------------
        # Pickup
        # -----------------------------------------------------

        picked_up_at = max(
            rider_arrived_at_store,
            packing_completed_at,
        ) + timedelta(
            seconds=random.randint(
                15,
                60,
            )
        )

        add_event(
            event_type="PICKED_UP",
            occurred_at=picked_up_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            delivery_id=delivery_id,
            store_id=store_id,
            rider_id=rider_id,
        )

        delivery["picked_up_at"] = (
            format_timestamp(
                picked_up_at
            )
        )

        fulfilment["status"] = (
            "HANDED_TO_RIDER"
        )

        # -----------------------------------------------------
        # Delivery starts
        # -----------------------------------------------------

        delivery_started_at = (
            picked_up_at
            + timedelta(
                seconds=random.randint(
                    15,
                    90,
                )
            )
        )

        add_event(
            event_type="DELIVERY_STARTED",
            occurred_at=delivery_started_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            delivery_id=delivery_id,
            store_id=store_id,
            rider_id=rider_id,
        )

        delivery[
            "delivery_started_at"
        ] = format_timestamp(
            delivery_started_at
        )

        delivery["status"] = (
            "IN_TRANSIT"
        )

        # -----------------------------------------------------
        # Transit
        # -----------------------------------------------------

        transit_duration = generate_transit_duration(
            distance_km=float(
                delivery["delivery_distance"]
            ),
            traffic_condition=(
                delivery["traffic_condition"]
            ),
            weather_condition=(
                delivery["weather_condition"]
            ),
        )

        delivered_at = (
            delivery_started_at
            + transit_duration
        )

        # -----------------------------------------------------
        # Delivered
        # -----------------------------------------------------

        add_event(
            event_type="DELIVERED",
            occurred_at=delivered_at,
            order_id=order_id,
            fulfilment_unit_id=fulfilment_id,
            delivery_id=delivery_id,
            store_id=store_id,
            rider_id=rider_id,
        )

        delivery["status"] = (
            "DELIVERED"
        )

        delivery["delivered_at"] = (
            format_timestamp(
                delivered_at
            )
        )

        fulfilment["status"] = (
            "COMPLETED"
        )

        fulfilment["completed_at"] = (
            format_timestamp(
                delivered_at
            )
        )

        # Rider becomes available again once
        # this delivery has completed.
        rider_available_at[
            rider_id
        ] = delivered_at

    # ---------------------------------------------------------
    # Derive final order state
    # ---------------------------------------------------------

    fulfilments_by_order: dict[
        str,
        list[dict],
    ] = {}

    for fulfilment in updated_fulfilments:
        fulfilments_by_order.setdefault(
            fulfilment["order_id"],
            [],
        ).append(fulfilment)

    for order in updated_orders:

        order_id = order["order_id"]

        order_fulfilments = (
            fulfilments_by_order.get(
                order_id,
                [],
            )
        )

        if not order_fulfilments:
            order["status"] = "FAILED"
            order["failure_reason"] = (
                "NO_FULFILMENT"
            )
            continue

        statuses = {
            fulfilment["status"]
            for fulfilment in order_fulfilments
        }

        if statuses == {"COMPLETED"}:

            order["status"] = "DELIVERED"

        elif "CANCELLED" in statuses:

            order["status"] = "CANCELLED"

            cancelled_fulfilment = next(
                fulfilment
                for fulfilment
                in order_fulfilments
                if fulfilment[
                    "status"
                ] == "CANCELLED"
            )

            order[
                "cancelled_at"
            ] = cancelled_fulfilment[
                "cancelled_at"
            ]

            order[
                "cancellation_reason"
            ] = cancelled_fulfilment[
                "cancellation_reason"
            ]

        elif "FAILED" in statuses:

            order["status"] = "FAILED"

            failed_fulfilment = next(
                fulfilment
                for fulfilment
                in order_fulfilments
                if fulfilment[
                    "status"
                ] == "FAILED"
            )

            order[
                "failure_reason"
            ] = failed_fulfilment[
                "failure_reason"
            ]

        else:

            order["status"] = "FULFILLING"

    # ---------------------------------------------------------
    # Chronological ordering
    # ---------------------------------------------------------

    events.sort(
        key=lambda event: (
            event["occurred_at"],
            event["event_id"],
        )
    )

    return (
        events,
        updated_orders,
        updated_fulfilments,
        updated_deliveries,
        updated_assignments,
    )


def save_events(
    events: list[dict],
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
        / "operational_events.csv"
    )

    fieldnames = [
        "event_id",
        "event_type",
        "occurred_at",
        "order_id",
        "fulfilment_unit_id",
        "delivery_id",
        "store_id",
        "rider_id",
        "reason",
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
        writer.writerows(events)

    print(
        f"Generated {len(events)} "
        "operational events"
    )

    print(
        f"Dataset saved to: {output_file}"
    )


def save_orders(
    orders: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    output_file = (
        output_dir
        / "orders.csv"
    )

    fieldnames = [
        "order_id",
        "customer_id",
        "created_at",
        "payment_success_at",
        "delivery_latitude",
        "delivery_longitude",
        "delivery_zone",
        "status",
        "cancelled_at",
        "cancellation_reason",
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
        writer.writerows(orders)


def save_fulfilment_units(
    fulfilment_units: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    output_file = (
        output_dir
        / "fulfilment_units.csv"
    )

    fieldnames = [
        "fulfilment_unit_id",
        "order_id",
        "store_id",
        "status",
        "assigned_to_store_at",
        "picking_started_at",
        "picking_completed_at",
        "packing_started_at",
        "packing_completed_at",
        "cancelled_at",
        "cancellation_reason",
        "failed_at",
        "failure_reason",
        "completed_at",
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
        writer.writerows(
            fulfilment_units
        )


def save_deliveries(
    deliveries: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
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
        writer.writerows(
            deliveries
        )


def save_assignments(
    assignments: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
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
        writer.writerows(
            assignments
        )


if __name__ == "__main__":

    orders = load_csv(
        "orders.csv"
    )

    fulfilment_units = load_csv(
        "fulfilment_units.csv"
    )

    deliveries = load_csv(
        "deliveries.csv"
    )

    riders = load_csv(
        "riders.csv"
    )

    stores = load_csv(
        "stores.csv"
    )

    (
        events,
        updated_orders,
        updated_fulfilments,
        updated_deliveries,
        updated_assignments,
    ) = generate_operational_events(
        orders=orders,
        fulfilment_units=fulfilment_units,
        deliveries=deliveries,
        riders=riders,
        stores=stores,
    )

    save_events(events)

    save_orders(
        updated_orders
    )

    save_fulfilment_units(
        updated_fulfilments
    )

    save_deliveries(
        updated_deliveries
    )

    save_assignments(
        updated_assignments
    )