from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, time
from threading import Lock
from typing import Dict, List, Optional

from . import schemas


def _time_overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return start_a < end_b and start_b < end_a


@dataclass
class Storage:
    _office_id: int = 0
    _floor_id: int = 0
    _desk_id: int = 0
    _reservation_id: int = 0
    _policy_id: int = 0
    offices: Dict[int, schemas.Office] = field(default_factory=dict)
    floors: Dict[int, schemas.Floor] = field(default_factory=dict)
    desks: Dict[int, schemas.Desk] = field(default_factory=dict)
    reservations: Dict[int, schemas.Reservation] = field(default_factory=dict)
    policies: Dict[int, schemas.Policy] = field(default_factory=dict)
    reservations_by_desk: Dict[int, List[int]] = field(default_factory=lambda: defaultdict(list))
    lock: Lock = field(default_factory=Lock)

    def _next_id(self, attr: str) -> int:
        current = getattr(self, attr) + 1
        setattr(self, attr, current)
        return current

    def create_office(self, payload: schemas.OfficeCreate) -> schemas.Office:
        with self.lock:
            office_id = self._next_id("_office_id")
            office = schemas.Office(id=office_id, **payload.model_dump())
            self.offices[office_id] = office
            return office

    def list_offices(self) -> List[schemas.Office]:
        return list(self.offices.values())

    def update_office(self, office_id: int, payload: schemas.OfficeUpdate) -> schemas.Office:
        with self.lock:
            office = self.offices.get(office_id)
            if office is None:
                raise KeyError("office")
            update_data = payload.model_dump(exclude_unset=True)
            if not update_data:
                return office
            office = office.model_copy(update=update_data)
            self.offices[office_id] = office
            return office

    def delete_office(self, office_id: int) -> None:
        with self.lock:
            if office_id not in self.offices:
                raise KeyError("office")
            if any(floor.office_id == office_id for floor in self.floors.values()):
                raise ValueError("Office has floors")
            del self.offices[office_id]

    def create_floor(self, payload: schemas.FloorCreate) -> schemas.Floor:
        with self.lock:
            if payload.office_id not in self.offices:
                raise KeyError("office")
            floor_id = self._next_id("_floor_id")
            floor = schemas.Floor(id=floor_id, **payload.model_dump())
            self.floors[floor_id] = floor
            return floor

    def list_floors(self, office_id: Optional[int] = None) -> List[schemas.Floor]:
        floors = list(self.floors.values())
        if office_id is None:
            return floors
        return [floor for floor in floors if floor.office_id == office_id]

    def update_floor(self, floor_id: int, payload: schemas.FloorUpdate) -> schemas.Floor:
        with self.lock:
            floor = self.floors.get(floor_id)
            if floor is None:
                raise KeyError("floor")
            update_data = payload.model_dump(exclude_unset=True)
            if not update_data:
                return floor
            floor = floor.model_copy(update=update_data)
            self.floors[floor_id] = floor
            return floor

    def delete_floor(self, floor_id: int) -> None:
        with self.lock:
            if floor_id not in self.floors:
                raise KeyError("floor")
            if any(desk.floor_id == floor_id for desk in self.desks.values()):
                raise ValueError("Floor has desks")
            del self.floors[floor_id]

    def create_desk(self, payload: schemas.DeskCreate) -> schemas.Desk:
        with self.lock:
            if payload.floor_id not in self.floors:
                raise KeyError("floor")
            if payload.type == "fixed" and not payload.assigned_to:
                raise ValueError("Fixed desks must have an assigned employee.")
            desk_id = self._next_id("_desk_id")
            desk_data = payload.model_dump()
            if desk_data.get("type") == "flex":
                desk_data["assigned_to"] = None
            desk = schemas.Desk(id=desk_id, **desk_data)
            self.desks[desk_id] = desk
            return desk

    def list_desks(self, floor_id: Optional[int] = None) -> List[schemas.Desk]:
        desks = list(self.desks.values())
        if floor_id is None:
            return desks
        return [desk for desk in desks if desk.floor_id == floor_id]

    def update_desk(self, desk_id: int, payload: schemas.DeskUpdate) -> schemas.Desk:
        with self.lock:
            desk = self.desks.get(desk_id)
            if desk is None:
                raise KeyError("desk")
            update_data = payload.model_dump(exclude_unset=True)
            if not update_data:
                return desk
            next_type = update_data.get("type", desk.type)
            next_assigned = update_data.get("assigned_to", desk.assigned_to)
            if next_type == "fixed" and not next_assigned:
                raise ValueError("Fixed desks must have an assigned employee.")
            if next_type == "flex":
                update_data["assigned_to"] = None
            desk = desk.model_copy(update=update_data)
            self.desks[desk_id] = desk
            return desk

    def delete_desk(self, desk_id: int) -> None:
        with self.lock:
            if desk_id not in self.desks:
                raise KeyError("desk")
            if any(res.desk_id == desk_id for res in self.reservations.values()):
                raise ValueError("Desk has reservations")
            del self.desks[desk_id]
            self.reservations_by_desk.pop(desk_id, None)

    def get_desk(self, desk_id: int) -> schemas.Desk:
        desk = self.desks.get(desk_id)
        if desk is None:
            raise KeyError("desk")
        return desk

    def check_availability(
        self,
        desk_id: int,
        reservation_date: date,
        start_time: time,
        end_time: time,
        user_id: Optional[str] = None,
    ) -> schemas.AvailabilityResponse:
        desk = self.get_desk(desk_id)
        if desk.type == "fixed" and not desk.assigned_to:
            return schemas.AvailabilityResponse(
                available=False,
                reason="Desk is fixed but has no assigned employee.",
            )
        if desk.type == "fixed" and desk.assigned_to and desk.assigned_to != user_id:
            return schemas.AvailabilityResponse(
                available=False,
                reason="Desk is assigned to another employee.",
            )
        for reservation_id in self.reservations_by_desk.get(desk_id, []):
            reservation = self.reservations[reservation_id]
            if reservation.status != "active":
                continue
            if reservation.reservation_date != reservation_date:
                continue
            if _time_overlaps(start_time, end_time, reservation.start_time, reservation.end_time):
                return schemas.AvailabilityResponse(
                    available=False,
                    reason="Desk already reserved for the requested time.",
                )
        return schemas.AvailabilityResponse(available=True)

    def create_reservation(self, payload: schemas.ReservationCreate) -> schemas.Reservation:
        with self.lock:
            availability = self.check_availability(
                payload.desk_id,
                payload.reservation_date,
                payload.start_time,
                payload.end_time,
                payload.user_id,
            )
            if not availability.available:
                raise ValueError(availability.reason or "Desk not available")
            reservation_id = self._next_id("_reservation_id")
            reservation = schemas.Reservation(id=reservation_id, **payload.model_dump())
            self.reservations[reservation_id] = reservation
            self.reservations_by_desk[payload.desk_id].append(reservation_id)
            return reservation

    def list_reservations(
        self,
        desk_id: Optional[int] = None,
        reservation_date: Optional[date] = None,
    ) -> List[schemas.Reservation]:
        reservations = list(self.reservations.values())
        if desk_id is not None:
            reservations = [res for res in reservations if res.desk_id == desk_id]
        if reservation_date is not None:
            reservations = [res for res in reservations if res.reservation_date == reservation_date]
        return reservations

    def cancel_reservation(self, reservation_id: int) -> schemas.Reservation:
        with self.lock:
            reservation = self.reservations.get(reservation_id)
            if reservation is None:
                raise KeyError("reservation")
            reservation = reservation.model_copy(update={"status": "cancelled"})
            self.reservations[reservation_id] = reservation
            return reservation

    def _validate_policy(self, payload: schemas.PolicyBase) -> None:
        if payload.min_days_ahead > payload.max_days_ahead:
            raise ValueError("Min days ahead must not exceed max days ahead.")
        if payload.min_duration_minutes > payload.max_duration_minutes:
            raise ValueError("Min duration must not exceed max duration.")

    def create_policy(self, payload: schemas.PolicyCreate) -> schemas.Policy:
        with self.lock:
            if payload.office_id is not None and payload.office_id not in self.offices:
                raise KeyError("office")
            self._validate_policy(payload)
            policy_id = self._next_id("_policy_id")
            policy = schemas.Policy(id=policy_id, **payload.model_dump())
            self.policies[policy_id] = policy
            return policy

    def list_policies(self, office_id: Optional[int] = None) -> List[schemas.Policy]:
        policies = list(self.policies.values())
        if office_id is None:
            return policies
        return [policy for policy in policies if policy.office_id in (None, office_id)]

    def update_policy(self, policy_id: int, payload: schemas.PolicyUpdate) -> schemas.Policy:
        with self.lock:
            policy = self.policies.get(policy_id)
            if policy is None:
                raise KeyError("policy")
            update_data = payload.model_dump(exclude_unset=True)
            if not update_data:
                return policy
            office_id = update_data.get("office_id", policy.office_id)
            if office_id is not None and office_id not in self.offices:
                raise KeyError("office")
            merged = policy.model_copy(update=update_data)
            self._validate_policy(merged)
            self.policies[policy_id] = merged
            return merged

    def delete_policy(self, policy_id: int) -> None:
        with self.lock:
            if policy_id not in self.policies:
                raise KeyError("policy")
            del self.policies[policy_id]
