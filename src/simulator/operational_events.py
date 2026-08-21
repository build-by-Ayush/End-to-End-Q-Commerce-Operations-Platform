from __future__ import annotations

import csv
import random
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
    order: dict,
) -> timedelta:
    """
    Generate a temporary picking duration.

    The current version uses a random baseline.
    Later this will incorporate order-item quantity
    and store staffing.
    """

    return timedelta(
        minutes=random.randint(2, 7),
        seconds=random.randint(0, 59),
    )


def generate_packing_duration() -> timedelta:
    """Generate a temporary packing duration."""

    return timedelta(
        minutes=random.randint(1, 3),
        seconds=random.randint(0, 30),
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


def generate_operational_events(
    orders: list[dict],
    fulfilment_units: list[dict],
    deliveries: list[dict],
    riders: list[dict],
    stores: list[dict],
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

    deliveries_by_fulfilment = {
        delivery["fulfilment_unit_id"]: delivery
        for delivery in deliveries
    }

    assignments_by_delivery: dict[
        str,
        list[dict],
    ] = {}

    for assignment in assignments:
        assignments_by_delivery.setdefault(
            assignment["delivery_id"],
            [],
        ).append(assignment)

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

    updated_assignments = [
        dict(assignment)
        for assignment in assignments
    ]

    events_by_order: dict[
        str,
        list[dict],
    ] = {}

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

        if order_id is not None:
            events_by_order.setdefault(
                order_id,
                [],
            ).append(event)

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

        picking_started_at = (
            assigned_to_store_at
            + timedelta(
                seconds=random.randint(
                    60,
                    180,
                )
            )
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

        picking_completed_at = (
            picking_started_at
            + generate_picking_duration(order)
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
            + generate_packing_duration()
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

        delivery_assignments = (
            assignments_by_delivery.get(
                delivery_id,
                [],
            )
        )

        accepted_assignment = next(
            (
                assignment
                for assignment
                in delivery_assignments
                if assignment["response"]
                == "ACCEPTED"
            ),
            None,
        )

        # No rider accepted the request.
        if accepted_assignment is None:

            failure_time = (
                packing_completed_at
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
        # Important timing correction
        # -----------------------------------------------------

        # The assignment generator was initially independent
        # of packing. We now make the accepted assignment occur
        # after packing is complete.
        #
        # This keeps the operational timeline coherent while
        # we eventually move assignment generation fully into
        # the lifecycle engine.

        rider_assigned_at = max(
            packing_completed_at
            + timedelta(
                seconds=random.randint(
                    30,
                    120,
                )
            ),
            parse_timestamp(
                accepted_assignment[
                    "responded_at"
                ]
            ),
        )

        # Update the assignment record so its timestamp agrees
        # with the operational lifecycle.
        accepted_assignment[
            "responded_at"
        ] = format_timestamp(
            rider_assigned_at
        )

        rider_id = accepted_assignment[
            "rider_id"
        ]

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

        base_transit_minutes = random.uniform(
            3,
            9,
        )

        if delivery[
            "traffic_condition"
        ] == "HIGH":

            base_transit_minutes += (
                random.uniform(
                    2,
                    5,
                )
            )

        elif delivery[
            "traffic_condition"
        ] == "SEVERE":

            base_transit_minutes += (
                random.uniform(
                    5,
                    10,
                )
            )

        if delivery[
            "weather_condition"
        ] == "RAIN":

            base_transit_minutes += (
                random.uniform(
                    1,
                    4,
                )
            )

        delivered_at = (
            delivery_started_at
            + timedelta(
                minutes=base_transit_minutes
            )
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

    orders = load_csv("orders.csv")

    fulfilment_units = load_csv(
        "fulfilment_units.csv"
    )

    deliveries = load_csv(
        "deliveries.csv"
    )

    assignments = load_csv(
        "rider_assignments.csv"
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
        assignments=assignments,
    )

    save_events(events)
    save_orders(updated_orders)
    save_fulfilment_units(
        updated_fulfilments
    )
    save_deliveries(
        updated_deliveries
    )
    save_assignments(
        updated_assignments
    )