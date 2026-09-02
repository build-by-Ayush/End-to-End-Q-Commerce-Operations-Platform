from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from simulator.config import CONFIG
from simulator.state import SimulationState
from simulator.time_utils import parse_timestamp


TIMESTAMP_FIELDS = {
    "created_at",
    "payment_success_at",
    "assigned_to_store_at",
    "picking_started_at",
    "picking_completed_at",
    "packing_started_at",
    "packing_completed_at",
    "cancelled_at",
    "failed_at",
    "completed_at",
    "rider_arrived_at_store",
    "picked_up_at",
    "delivery_started_at",
    "delivered_at",
    "offered_at",
    "responded_at",
    "expired_at",
    "occurred_at",
}


class ValidationResult:
    """Collect validation errors and warnings."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def print_report(self) -> None:
        print("\n" + "=" * 60)
        print("SIMULATION VALIDATION REPORT")
        print("=" * 60)

        if self.errors:
            print(f"\nERRORS: {len(self.errors)}")

            for error in self.errors:
                print(f"  [ERROR] {error}")
        else:
            print("\nERRORS: 0")

        if self.warnings:
            print(f"\nWARNINGS: {len(self.warnings)}")

            for warning in self.warnings:
                print(f"  [WARNING] {warning}")
        else:
            print("WARNINGS: 0")

        print()

        if self.passed:
            print("VALIDATION RESULT: PASS")
        else:
            print("VALIDATION RESULT: FAIL")

        print("=" * 60)


def parse_optional_timestamp(
    value: str | None,
) -> datetime | None:
    """Parse a nullable simulator timestamp."""

    if value is None:
        return None

    if value == "":
        return None

    return parse_timestamp(value)


def validate_unique_ids(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate uniqueness of primary/business identifiers."""

    datasets = {
        "customers": (
            state.customers,
            "customer_id",
        ),
        "stores": (
            state.stores,
            "store_id",
        ),
        "riders": (
            state.riders,
            "rider_id",
        ),
        "orders": (
            state.orders,
            "order_id",
        ),
        "fulfilment_units": (
            state.fulfilment_units,
            "fulfilment_unit_id",
        ),
        "order_items": (
            state.order_items,
            "order_item_id",
        ),
        "deliveries": (
            state.deliveries,
            "delivery_id",
        ),
        "rider_assignments": (
            state.rider_assignments,
            "assignment_id",
        ),
        "operational_events": (
            state.operational_events,
            "event_id",
        ),
        "store_staffing": (
            state.store_staffing,
            "staffing_snapshot_id",
        ),
    }

    for dataset_name, (
        rows,
        id_column,
    ) in datasets.items():

        seen: set[str] = set()

        for row in rows:
            identifier = row.get(id_column)

            if not identifier:
                result.error(
                    f"{dataset_name}: missing {id_column}"
                )
                continue

            if identifier in seen:
                result.error(
                    f"{dataset_name}: duplicate "
                    f"{id_column}={identifier}"
                )

            seen.add(identifier)


def validate_foreign_keys(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate mandatory parent-child relationships."""

    customer_ids = {
        row["customer_id"]
        for row in state.customers
    }

    store_ids = {
        row["store_id"]
        for row in state.stores
    }

    rider_ids = {
        row["rider_id"]
        for row in state.riders
    }

    order_ids = {
        row["order_id"]
        for row in state.orders
    }

    fulfilment_ids = {
        row["fulfilment_unit_id"]
        for row in state.fulfilment_units
    }

    delivery_ids = {
        row["delivery_id"]
        for row in state.deliveries
    }

    for row in state.orders:

        if row["customer_id"] not in customer_ids:
            result.error(
                "orders: unknown customer_id "
                f"{row['customer_id']} for "
                f"{row['order_id']}"
            )

    for row in state.fulfilment_units:

        if row["order_id"] not in order_ids:
            result.error(
                "fulfilment_units: unknown order_id "
                f"{row['order_id']} for "
                f"{row['fulfilment_unit_id']}"
            )

        if row["store_id"] not in store_ids:
            result.error(
                "fulfilment_units: unknown store_id "
                f"{row['store_id']} for "
                f"{row['fulfilment_unit_id']}"
            )

    for row in state.order_items:

        if row["order_id"] not in order_ids:
            result.error(
                "order_items: unknown order_id "
                f"{row['order_id']} for "
                f"{row['order_item_id']}"
            )

        if (
            row["fulfilment_unit_id"]
            not in fulfilment_ids
        ):
            result.error(
                "order_items: unknown "
                "fulfilment_unit_id "
                f"{row['fulfilment_unit_id']} for "
                f"{row['order_item_id']}"
            )

    for row in state.deliveries:

        if (
            row["fulfilment_unit_id"]
            not in fulfilment_ids
        ):
            result.error(
                "deliveries: unknown "
                "fulfilment_unit_id "
                f"{row['fulfilment_unit_id']} for "
                f"{row['delivery_id']}"
            )

        rider_id = row.get("rider_id")

        if rider_id and rider_id not in rider_ids:
            result.error(
                "deliveries: unknown rider_id "
                f"{rider_id} for "
                f"{row['delivery_id']}"
            )

    for row in state.rider_assignments:

        if row["delivery_id"] not in delivery_ids:
            result.error(
                "rider_assignments: unknown "
                "delivery_id "
                f"{row['delivery_id']} for "
                f"{row['assignment_id']}"
            )

        if row["rider_id"] not in rider_ids:
            result.error(
                "rider_assignments: unknown rider_id "
                f"{row['rider_id']} for "
                f"{row['assignment_id']}"
            )

    for row in state.operational_events:

        optional_references = {
            "order_id": order_ids,
            "fulfilment_unit_id": fulfilment_ids,
            "delivery_id": delivery_ids,
            "store_id": store_ids,
            "rider_id": rider_ids,
        }

        for column, valid_ids in optional_references.items():

            value = row.get(column)

            if value and value not in valid_ids:
                result.error(
                    "operational_events: unknown "
                    f"{column}={value} for "
                    f"{row['event_id']}"
                )

    for row in state.store_staffing:

        if row["store_id"] not in store_ids:
            result.error(
                "store_staffing: unknown store_id "
                f"{row['store_id']} for "
                f"{row['staffing_snapshot_id']}"
            )


def validate_order_item_ownership(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Ensure an order item belongs to a fulfilment unit
    whose parent order is the same order.
    """

    fulfilments_by_id = {
        row["fulfilment_unit_id"]: row
        for row in state.fulfilment_units
    }

    accepted_riders_by_delivery = defaultdict(set)

    for assignment in state.rider_assignments:
        if assignment["response"] == "ACCEPTED":
            accepted_riders_by_delivery[
                assignment["delivery_id"]
            ].add(assignment["rider_id"])

    for item in state.order_items:

        fulfilment = fulfilments_by_id.get(
            item["fulfilment_unit_id"]
        )

        if fulfilment is None:
            continue

        if (
            fulfilment["order_id"]
            != item["order_id"]
        ):
            result.error(
                "order_items: order/fulfilment mismatch "
                f"for {item['order_item_id']} - "
                f"order_id={item['order_id']}, "
                f"fulfilment belongs to "
                f"{fulfilment['order_id']}"
            )


def validate_fulfilment_item_coverage(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Every fulfilment unit representing active work should
    have at least one order item.
    """

    item_count_by_fulfilment = defaultdict(int)

    for item in state.order_items:
        item_count_by_fulfilment[
            item["fulfilment_unit_id"]
        ] += 1

    for fulfilment in state.fulfilment_units:

        fulfilment_id = (
            fulfilment["fulfilment_unit_id"]
        )

        item_count = item_count_by_fulfilment.get(
            fulfilment_id,
            0,
        )

        if item_count == 0:
            result.error(
                "fulfilment_units: fulfilment unit "
                f"{fulfilment_id} has no order items"
            )


def validate_delivery_cardinality(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Ensure every fulfilment operation has exactly one delivery row."""

    deliveries_by_fulfilment = defaultdict(list)

    for delivery in state.deliveries:
        deliveries_by_fulfilment[
            delivery["fulfilment_unit_id"]
        ].append(delivery["delivery_id"])

    for fulfilment in state.fulfilment_units:
        fulfilment_id = fulfilment["fulfilment_unit_id"]
        delivery_ids = deliveries_by_fulfilment.get(
            fulfilment_id,
            [],
        )

        if len(delivery_ids) != 1:
            result.error(
                "fulfilment_units: expected exactly one delivery "
                f"for {fulfilment_id}, found {len(delivery_ids)}"
            )


def validate_order_final_states(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate pessimistic parent status for split fulfilment."""

    fulfilments_by_order = defaultdict(list)

    for fulfilment in state.fulfilment_units:
        fulfilments_by_order[fulfilment["order_id"]].append(
            fulfilment
        )

    for order in state.orders:
        fulfilments = fulfilments_by_order.get(order["order_id"], [])

        if not fulfilments:
            result.error(
                "orders: order has no fulfilment units: "
                f"{order['order_id']}"
            )
            continue

        statuses = {
            fulfilment["status"]
            for fulfilment in fulfilments
        }

        if statuses == {"COMPLETED"}:
            expected_status = "DELIVERED"
        elif "CANCELLED" in statuses:
            expected_status = "CANCELLED"
        elif "FAILED" in statuses:
            expected_status = "FAILED"
        else:
            expected_status = "FULFILLING"

        if order.get("status") != expected_status:
            result.error(
                "orders: status does not match fulfilment outcomes "
                f"for {order['order_id']}: "
                f"expected {expected_status}, found "
                f"{order.get('status')}"
            )


def validate_timestamps(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Validate that timestamps can be parsed.

    Ordering is checked separately.
    """

    datasets = [
        (
            "orders",
            state.orders,
            [
                "created_at",
                "payment_success_at",
                "cancelled_at",
            ],
        ),
        (
            "fulfilment_units",
            state.fulfilment_units,
            [
                "assigned_to_store_at",
                "picking_started_at",
                "picking_completed_at",
                "packing_started_at",
                "packing_completed_at",
                "cancelled_at",
                "failed_at",
                "completed_at",
            ],
        ),
        (
            "deliveries",
            state.deliveries,
            [
                "rider_arrived_at_store",
                "picked_up_at",
                "delivery_started_at",
                "delivered_at",
                "cancelled_at",
                "failed_at",
            ],
        ),
        (
            "rider_assignments",
            state.rider_assignments,
            [
                "offered_at",
                "responded_at",
                "expired_at",
            ],
        ),
        (
            "operational_events",
            state.operational_events,
            [
                "occurred_at",
            ],
        ),
        (
            "store_staffing",
            state.store_staffing,
            [
                "recorded_at",
            ],
        ),
    ]

    for dataset_name, rows, columns in datasets:

        for row in rows:

            for column in columns:

                value = row.get(column)

                if not value:
                    continue

                try:
                    parse_timestamp(value)

                except ValueError:
                    result.error(
                        f"{dataset_name}: invalid "
                        f"timestamp {column}="
                        f"{value!r}"
                    )


def validate_simulation_calendar(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Ensure operational timestamps stay inside the shared calendar."""

    datasets = [
        ("orders", state.orders, ["created_at", "payment_success_at"]),
        (
            "fulfilment_units",
            state.fulfilment_units,
            [
                "assigned_to_store_at",
                "picking_started_at",
                "picking_completed_at",
                "packing_started_at",
                "packing_completed_at",
                "cancelled_at",
                "failed_at",
                "completed_at",
            ],
        ),
        (
            "deliveries",
            state.deliveries,
            [
                "rider_arrived_at_store",
                "picked_up_at",
                "delivery_started_at",
                "delivered_at",
                "cancelled_at",
                "failed_at",
            ],
        ),
        (
            "rider_assignments",
            state.rider_assignments,
            ["offered_at", "responded_at", "expired_at"],
        ),
        ("operational_events", state.operational_events, ["occurred_at"]),
        ("store_staffing", state.store_staffing, ["recorded_at"]),
    ]

    for dataset_name, rows, columns in datasets:
        for row in rows:
            for column in columns:
                raw_value = row.get(column)

                if not raw_value:
                    continue

                try:
                    value = parse_timestamp(raw_value)
                except ValueError:
                    continue

                if not (
                    CONFIG.simulation_start
                    <= value
                    < CONFIG.simulation_end
                ):
                    result.error(
                        f"{dataset_name}: {column} outside "
                        "simulation calendar for "
                        f"{row}"
                    )


def validate_store_staffing_coverage(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate one coherent staffing observation per store interval."""

    expected_timestamps = {
        CONFIG.simulation_start + timedelta(
            hours=offset
        )
        for offset in range(
            0,
            CONFIG.simulation_hours,
            CONFIG.staffing_interval_hours,
        )
    }

    observations_by_store = defaultdict(list)

    for row in state.store_staffing:
        try:
            recorded_at = parse_timestamp(row["recorded_at"])
        except ValueError:
            continue

        observations_by_store[row["store_id"]].append(
            (recorded_at, row)
        )

        try:
            pickers_scheduled = int(row["pickers_scheduled"])
            pickers_available = int(row["pickers_available"])
            packers_scheduled = int(row["packers_scheduled"])
            packers_available = int(row["packers_available"])
        except (TypeError, ValueError):
            result.error(
                "store_staffing: non-integer staffing values for "
                f"{row['staffing_snapshot_id']}"
            )
            continue

        if (
            pickers_scheduled <= 0
            or packers_scheduled <= 0
            or pickers_available < 0
            or packers_available < 0
            or pickers_available > pickers_scheduled
            or packers_available > packers_scheduled
        ):
            result.error(
                "store_staffing: invalid scheduled/available "
                f"counts for {row['staffing_snapshot_id']}"
            )

    for store in state.stores:
        store_id = store["store_id"]
        observations = observations_by_store.get(store_id, [])
        timestamps = [item[0] for item in observations]

        if len(timestamps) != len(expected_timestamps):
            result.error(
                "store_staffing: incorrect observation count for "
                f"{store_id}: expected {len(expected_timestamps)}, "
                f"found {len(timestamps)}"
            )

        if set(timestamps) != expected_timestamps:
            result.error(
                "store_staffing: incomplete or duplicate calendar "
                f"coverage for {store_id}"
            )


def validate_order_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate basic order-level timestamp ordering."""

    for order in state.orders:

        created_at = parse_optional_timestamp(
            order.get("created_at")
        )

        payment_success_at = (
            parse_optional_timestamp(
                order.get(
                    "payment_success_at"
                )
            )
        )

        if (
            created_at is not None
            and payment_success_at is not None
            and payment_success_at < created_at
        ):
            result.error(
                "orders: payment_success_at "
                f"occurs before created_at for "
                f"{order['order_id']}"
            )

        status = order.get("status")

        if status == "DELIVERED":

            if order.get("cancelled_at"):
                result.error(
                    "orders: delivered order has "
                    f"cancelled_at for "
                    f"{order['order_id']}"
                )

            if order.get("cancellation_reason"):
                result.error(
                    "orders: delivered order has "
                    "cancellation_reason for "
                    f"{order['order_id']}"
                )

            if order.get("failure_reason"):
                result.error(
                    "orders: delivered order has "
                    "failure_reason for "
                    f"{order['order_id']}"
                )


def validate_fulfilment_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate fulfilment timestamp ordering and status."""

    for fulfilment in state.fulfilment_units:

        values = [
            (
                "assigned_to_store_at",
                fulfilment.get(
                    "assigned_to_store_at"
                ),
            ),
            (
                "picking_started_at",
                fulfilment.get(
                    "picking_started_at"
                ),
            ),
            (
                "picking_completed_at",
                fulfilment.get(
                    "picking_completed_at"
                ),
            ),
            (
                "packing_started_at",
                fulfilment.get(
                    "packing_started_at"
                ),
            ),
            (
                "packing_completed_at",
                fulfilment.get(
                    "packing_completed_at"
                ),
            ),
            (
                "completed_at",
                fulfilment.get(
                    "completed_at"
                ),
            ),
        ]

        previous_name: str | None = None
        previous_value: datetime | None = None

        for name, raw_value in values:

            current_value = parse_optional_timestamp(
                raw_value
            )

            if current_value is None:
                continue

            if (
                previous_value is not None
                and current_value < previous_value
            ):
                result.error(
                    "fulfilment_units: timestamp "
                    f"ordering error for "
                    f"{fulfilment['fulfilment_unit_id']}: "
                    f"{previous_name} > {name}"
                )

            previous_name = name
            previous_value = current_value

        status = fulfilment.get("status")

        if status == "COMPLETED":

            if not fulfilment.get(
                "completed_at"
            ):
                result.error(
                    "fulfilment_units: COMPLETED "
                    f"unit has no completed_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

        if status == "CANCELLED":

            if not fulfilment.get(
                "cancelled_at"
            ):
                result.error(
                    "fulfilment_units: CANCELLED "
                    f"unit has no cancelled_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

            if not fulfilment.get(
                "cancellation_reason"
            ):
                result.error(
                    "fulfilment_units: CANCELLED "
                    f"unit has no cancellation_reason: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

        if status == "FAILED":

            if not fulfilment.get(
                "failed_at"
            ):
                result.error(
                    "fulfilment_units: FAILED "
                    f"unit has no failed_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

            if not fulfilment.get(
                "failure_reason"
            ):
                result.error(
                    "fulfilment_units: FAILED "
                    f"unit has no failure_reason: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )


def validate_delivery_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate delivery status and timestamp consistency."""

    for delivery in state.deliveries:

        delivery_id = delivery["delivery_id"]
        status = delivery["status"]

        rider_arrived = parse_optional_timestamp(
            delivery.get(
                "rider_arrived_at_store"
            )
        )

        picked_up = parse_optional_timestamp(
            delivery.get("picked_up_at")
        )

        delivery_started = (
            parse_optional_timestamp(
                delivery.get(
                    "delivery_started_at"
                )
            )
        )

        delivered = parse_optional_timestamp(
            delivery.get("delivered_at")
        )

        if (
            rider_arrived is not None
            and picked_up is not None
            and picked_up < rider_arrived
        ):
            result.error(
                "deliveries: picked_up_at occurs "
                f"before rider_arrived_at_store "
                f"for {delivery_id}"
            )

        if (
            picked_up is not None
            and delivery_started is not None
            and delivery_started < picked_up
        ):
            result.error(
                "deliveries: delivery_started_at "
                "occurs before picked_up_at for "
                f"{delivery_id}"
            )

        if (
            delivery_started is not None
            and delivered is not None
            and delivered < delivery_started
        ):
            result.error(
                "deliveries: delivered_at occurs "
                "before delivery_started_at for "
                f"{delivery_id}"
            )

        if status == "DELIVERED":

            required_fields = [
                "rider_id",
                "rider_arrived_at_store",
                "picked_up_at",
                "delivery_started_at",
                "delivered_at",
            ]

            for field in required_fields:

                if not delivery.get(field):
                    result.error(
                        "deliveries: DELIVERED delivery "
                        f"{delivery_id} missing "
                        f"{field}"
                    )

        if status == "FAILED":

            if not delivery.get(
                "failed_at"
            ):
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} missing failed_at"
                )

            if not delivery.get(
                "failure_reason"
            ):
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} missing "
                    "failure_reason"
                )

        if status == "CANCELLED":

            if not delivery.get(
                "cancelled_at"
            ):
                result.error(
                    "deliveries: CANCELLED delivery "
                    f"{delivery_id} missing "
                    "cancelled_at"
                )

            if not delivery.get(
                "cancellation_reason"
            ):
                result.error(
                    "deliveries: CANCELLED delivery "
                    f"{delivery_id} missing "
                    "cancellation_reason"
                )


def validate_assignment_semantics(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate accepted/rejected/expired rider offers."""

    for assignment in state.rider_assignments:

        response = assignment["response"]

        if response not in {
            "ACCEPTED",
            "REJECTED",
            "EXPIRED",
        }:
            result.error(
                "rider_assignments: unsupported response "
                f"{response!r} for "
                f"{assignment['assignment_id']}"
            )
            continue

        responded_at = assignment.get(
            "responded_at"
        )

        expired_at = assignment.get(
            "expired_at"
        )

        if response == "ACCEPTED":

            if not responded_at:
                result.error(
                    "rider_assignments: ACCEPTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no responded_at"
                )

            if expired_at:
                result.error(
                    "rider_assignments: ACCEPTED "
                    f"assignment {assignment['assignment_id']} "
                    "has expired_at"
                )

        elif response == "REJECTED":

            if not responded_at:
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no responded_at"
                )

            if expired_at:
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has expired_at"
                )

            if not assignment.get(
                "rejection_reason"
            ):
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no rejection_reason"
                )

        elif response == "EXPIRED":

            if responded_at:
                result.error(
                    "rider_assignments: EXPIRED "
                    f"assignment {assignment['assignment_id']} "
                    "should not have responded_at"
                )

            if not expired_at:
                result.error(
                    "rider_assignments: EXPIRED "
                    f"assignment {assignment['assignment_id']} "
                    "has no expired_at"
                )

        offered_at_value = parse_optional_timestamp(
            assignment.get("offered_at")
        )
        terminal_raw_value = responded_at or expired_at
        terminal_value = parse_optional_timestamp(
            terminal_raw_value
        )

        if (
            offered_at_value is not None
            and terminal_value is not None
            and terminal_value < offered_at_value
        ):
            result.error(
                "rider_assignments: response precedes offer for "
                f"{assignment['assignment_id']}"
            )


def validate_assignment_events(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Validate that accepted assignments become
    RIDER_ASSIGNED events.
    """

    accepted_assignments = [
        assignment
        for assignment in state.rider_assignments
        if assignment["response"] == "ACCEPTED"
    ]

    rider_assigned_events = [
        event
        for event in state.operational_events
        if event["event_type"]
        == "RIDER_ASSIGNED"
    ]

    events_by_delivery: dict[
        str,
        list[dict],
    ] = defaultdict(list)

    for event in rider_assigned_events:
        events_by_delivery[
            event["delivery_id"]
        ].append(event)

    for assignment in accepted_assignments:

        matching_events = [
            event
            for event in events_by_delivery[
                assignment["delivery_id"]
            ]
            if event["rider_id"]
            == assignment["rider_id"]
        ]

        if len(matching_events) != 1:
            result.error(
                "rider_assignments: accepted "
                f"assignment {assignment['assignment_id']} "
                "does not map to exactly one "
                "matching RIDER_ASSIGNED event"
            )


def validate_delivery_fulfilment_consistency(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate delivery/fulfilment final-state consistency."""

    fulfilments_by_id = {
        row["fulfilment_unit_id"]: row
        for row in state.fulfilment_units
    }

    for delivery in state.deliveries:

        fulfilment = fulfilments_by_id.get(
            delivery["fulfilment_unit_id"]
        )

        if fulfilment is None:
            continue

        delivery_status = delivery["status"]
        fulfilment_status = fulfilment["status"]

        if (
            delivery_status == "DELIVERED"
            and fulfilment_status
            != "COMPLETED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "DELIVERED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        if (
            delivery_status == "CANCELLED"
            and fulfilment_status
            != "CANCELLED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "CANCELLED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        if (
            delivery_status == "FAILED"
            and fulfilment_status
            != "FAILED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "FAILED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        delivery_rider = delivery.get(
            "rider_id"
        )

        if delivery_rider:

            accepted_riders = accepted_riders_by_delivery.get(
                delivery["delivery_id"],
                set(),
            )

            if accepted_riders != {delivery_rider}:
                result.error(
                    "state mismatch: delivery "
                    f"{delivery['delivery_id']} has "
                    f"rider_id={delivery_rider}, but accepted "
                    f"riders are {sorted(accepted_riders)}"
                )


def validate_event_presence(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate required lifecycle events for final states."""

    events_by_delivery: dict[
        str,
        list[dict],
    ] = defaultdict(list)

    for event in state.operational_events:

        delivery_id = event.get(
            "delivery_id"
        )

        if delivery_id:
            events_by_delivery[
                delivery_id
            ].append(event)

    for delivery in state.deliveries:

        delivery_id = delivery["delivery_id"]
        status = delivery["status"]

        event_types = {
            event["event_type"]
            for event in events_by_delivery[
                delivery_id
            ]
        }

        if status == "DELIVERED":

            required_events = {
                "RIDER_ASSIGNED",
                "RIDER_ARRIVED_AT_STORE",
                "PICKED_UP",
                "DELIVERY_STARTED",
                "DELIVERED",
            }

            missing = (
                required_events
                - event_types
            )

            for event_type in sorted(missing):
                result.error(
                    "deliveries: DELIVERED delivery "
                    f"{delivery_id} missing "
                    f"event {event_type}"
                )

        if status == "FAILED":

            has_delivery_failure = (
                "DELIVERY_FAILED"
                in event_types
            )

            has_fulfilment_failure = (
                "FULFILMENT_FAILED"
                in event_types
            )

            if not (
                has_delivery_failure
                or has_fulfilment_failure
            ):
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} has neither "
                    "DELIVERY_FAILED nor "
                    "FULFILMENT_FAILED event"
                )


def validate_rider_concurrency(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Check that a rider does not have overlapping active-delivery
    intervals. A rider is active from assignment acceptance, not only
    from last-mile transit.
    """

    deliveries_by_rider: dict[
        str,
        list[tuple[datetime, datetime, str]],
    ] = defaultdict(list)

    accepted_at_by_delivery = {}

    for assignment in state.rider_assignments:
        if assignment["response"] == "ACCEPTED":
            accepted_at_by_delivery[
                assignment["delivery_id"]
            ] = parse_optional_timestamp(
                assignment.get("responded_at")
            )

    for delivery in state.deliveries:

        rider_id = delivery.get("rider_id")

        if not rider_id:
            continue

        start = accepted_at_by_delivery.get(
            delivery["delivery_id"]
        )

        end = parse_optional_timestamp(
            delivery.get("delivered_at")
            or delivery.get("failed_at")
            or delivery.get("cancelled_at")
        )

        if start is None or end is None:
            continue

        deliveries_by_rider[
            rider_id
        ].append(
            (
                start,
                end,
                delivery["delivery_id"],
            )
        )

    for rider_id, intervals in (
        deliveries_by_rider.items()
    ):

        intervals.sort(
            key=lambda item: item[0]
        )

        for index in range(
            1,
            len(intervals),
        ):

            previous_start, previous_end, previous_id = (
                intervals[index - 1]
            )

            current_start, current_end, current_id = (
                intervals[index]
            )

            if current_start < previous_end:
                result.error(
                    "riders: overlapping deliveries "
                    f"for {rider_id}: "
                    f"{previous_id} overlaps "
                    f"{current_id}"
                )


def validate_operational_outcomes(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Check terminal outcomes and derive SLA from PAYMENT_SUCCESS."""

    if not state.deliveries:
        result.error("deliveries: dataset is empty")
        return

    fulfilments_by_id = {
        fulfilment["fulfilment_unit_id"]: fulfilment
        for fulfilment in state.fulfilment_units
    }
    orders_by_id = {
        order["order_id"]: order
        for order in state.orders
    }

    delivered_count = 0
    on_target_count = 0
    grace_count = 0
    breach_count = 0

    for delivery in state.deliveries:
        status = delivery.get("status")

        if status not in {"DELIVERED", "CANCELLED", "FAILED"}:
            result.error(
                "deliveries: non-terminal status for "
                f"{delivery['delivery_id']}: {status}"
            )
            continue

        if status != "DELIVERED":
            continue

        delivered_count += 1

        fulfilment = fulfilments_by_id.get(
            delivery["fulfilment_unit_id"]
        )

        if fulfilment is None:
            continue

        order = orders_by_id.get(fulfilment["order_id"])

        if order is None:
            continue

        payment_success_at = parse_optional_timestamp(
            order.get("payment_success_at")
        )
        delivered_at = parse_optional_timestamp(
            delivery.get("delivered_at")
        )

        if payment_success_at is None or delivered_at is None:
            result.error(
                "deliveries: cannot derive SLA for "
                f"{delivery['delivery_id']}"
            )
            continue

        elapsed_minutes = (
            delivered_at - payment_success_at
        ).total_seconds() / 60

        if elapsed_minutes < 0:
            result.error(
                "deliveries: delivery precedes payment success for "
                f"{delivery['delivery_id']}"
            )
        elif elapsed_minutes <= CONFIG.sla_target_minutes:
            on_target_count += 1
        elif elapsed_minutes <= (
            CONFIG.sla_target_minutes
            + CONFIG.sla_grace_minutes
        ):
            grace_count += 1
        else:
            breach_count += 1

    success_rate = delivered_count / len(state.deliveries)

    if success_rate < 0.80:
        result.error(
            "deliveries: successful-delivery rate is below the "
            f"minimum credible baseline: {success_rate:.1%}"
        )

    if delivered_count and breach_count / delivered_count > 0.25:
        result.warning(
            "deliveries: more than 25% of delivered operations "
            "breach the 25-minute SLA threshold "
            f"(on target={on_target_count}, "
            f"within grace={grace_count}, breach={breach_count})"
        )


def validate_state(
    state: SimulationState,
) -> ValidationResult:
    """Run the complete clean-data validation suite."""

    result = ValidationResult()

    validate_unique_ids(
        state,
        result,
    )

    validate_foreign_keys(
        state,
        result,
    )

    validate_order_item_ownership(
        state,
        result,
    )

    validate_fulfilment_item_coverage(
        state,
        result,
    )

    validate_delivery_cardinality(
        state,
        result,
    )

    validate_timestamps(
        state,
        result,
    )

    validate_simulation_calendar(
        state,
        result,
    )

    validate_store_staffing_coverage(
        state,
        result,
    )

    validate_order_lifecycle(
        state,
        result,
    )

    validate_order_final_states(
        state,
        result,
    )

    validate_fulfilment_lifecycle(
        state,
        result,
    )

    validate_delivery_lifecycle(
        state,
        result,
    )

    validate_assignment_semantics(
        state,
        result,
    )

    validate_assignment_events(
        state,
        result,
    )

    validate_delivery_fulfilment_consistency(
        state,
        result,
    )

    validate_event_presence(
        state,
        result,
    )

    validate_rider_concurrency(
        state,
        result,
    )

    validate_operational_outcomes(
        state,
        result,
    )

    return result
