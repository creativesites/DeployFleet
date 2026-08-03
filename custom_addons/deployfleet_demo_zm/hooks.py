"""Generates a full demo dataset for a fictional Zambian trucking company,
"CreativeSites Logistics", touching every installed DeployFleet module so
a fresh demo install has something real to look at end to end - company/
depots/customers/vehicles/drivers/routes/contracts, shipments carried all
the way through dispatch -> trip -> delivery -> invoice -> (attempted)
ZRA submission, fuel logs with a deliberate anomaly, maintenance/workshop
history, compliance/insurance documents (including one deliberately
expired, to exercise the compliance-override audit trail), payroll/leave/
advances/loans, and a few AI action-request examples in different states.

Runs entirely through each model's normal `create()`/`action_*()` methods,
not raw SQL or bypassed-validation record dumps - a demo company should be
built the same way a real one would be, so it exercises the same
constraints and event-bus side effects (auto-generated invoices, fired
notifications, ...) a real customer's data would.

Deliberately never calls `deployfleet.ai.core.complete()` - that would
spend real tokens/cost against whatever AI provider key is actually
configured on the target database, which could be a real key on a live
server. The AI agent catalog is demonstrated by its presence and
permission configuration, not by an actual LLM call made during install.

Deliberately leaves `deployfleet.zra.config` and any Expo push-device
registration alone (no demo device tokens) so no outbound network call is
attempted during install - a demo invoice's ZRA submission will land in
`error` state with "No ZRA API base URL configured", which is an honest,
fast, offline-safe outcome, not a bug in this generator.
"""

import logging
from datetime import date, timedelta

from odoo import fields

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    # env passed to a post_init_hook is already superuser-bound - kept that
    # way throughout so this one-time seeding script never trips over an
    # ordinary ACL wall. `admin` is only used where a real user context is
    # actually needed: the AI action-approval checks (has_group()) and
    # cosmetic "recorded by" attribution.
    admin = env.ref("base.user_admin")

    company = _setup_company(env)
    depots = _create_depots(env)
    customers = _create_customers_and_contracts(env)
    vehicles = _create_vehicles(env)
    drivers = _create_drivers(env)
    routes = _create_routes(env, depots)
    _create_insurance_and_compliance(env, vehicles)
    _create_maintenance_and_workshop(env, vehicles)
    _create_parts_and_tyres(env, vehicles)
    _create_assets(env)
    _create_fuel_logs(env, vehicles)
    _run_operations(env, customers, depots, routes, vehicles, drivers)
    _create_hr_extras(env, drivers, admin)
    _create_payslips(env, drivers)
    _create_ai_action_requests(env, admin)
    _create_whatsapp_demo_config(env, company)
    _run_ai_agents_crons(env)
    _logger.info("deployfleet_demo_zm: demo dataset generated for %s", company.display_name)


# ---------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------

def _setup_company(env):
    company = env.ref("base.main_company")
    zmw = env.ref("base.ZMW")
    if not zmw.active:
        zmw.active = True
    zambia = env.ref("base.zm")
    company.write({"name": "CreativeSites Logistics", "country_id": zambia.id, "currency_id": zmw.id})
    return company


# ---------------------------------------------------------------------
# Depots, customers, contracts, rate cards
# ---------------------------------------------------------------------

def _create_depots(env):
    depot_model = env["deployfleet.depot"]
    names = ["Lusaka HQ", "Ndola", "Kitwe", "Livingstone", "Chingola"]
    return {name: depot_model.create({"name": name, "city": name.split(" ", maxsplit=1)[0]}) for name in names}


def _create_customers_and_contracts(env):
    contract_model = env["deployfleet.contract"]
    rate_card_model = env["deployfleet.rate.card"]
    partner_model = env["res.partner"]

    specs = [
        ("Kwacha Traders Ltd", "per_trip", 4500.0),
        ("Copperbelt Mining Supplies", "per_tonnage", 220.0),
        ("Livingstone Tourism Group", "per_trip", 5200.0),
        ("Lusaka Retail Holdings", "per_distance", 42.0),
        ("Ndola Agro Processors", "per_tonnage", 195.0),
    ]
    customers = {}
    for name, rate_basis, rate in specs:
        partner = partner_model.create({"name": name, "is_company": True})
        contract = contract_model.create({"customer_id": partner.id, "rate_basis": rate_basis})
        contract.action_activate()
        rate_card_model.create({"contract_id": contract.id, "unit_amount": rate})
        customers[name] = {"partner": partner, "contract": contract}
    return customers


# ---------------------------------------------------------------------
# Fleet: vehicles and drivers
# ---------------------------------------------------------------------

def _get_or_create_model(env, brand_name, model_name):
    brand = env["fleet.vehicle.model.brand"].search([("name", "=", brand_name)], limit=1)
    if not brand:
        brand = env["fleet.vehicle.model.brand"].create({"name": brand_name})
    model = env["fleet.vehicle.model"].search([("name", "=", model_name), ("brand_id", "=", brand.id)], limit=1)
    if not model:
        model = env["fleet.vehicle.model"].create({"name": model_name, "brand_id": brand.id})
    return model


def _create_vehicles(env):
    vehicle_model = env["deployfleet.vehicle"]
    type_rigid = env.ref("deployfleet_core.vehicle_type_rigid")
    type_articulated = env.ref("deployfleet_core.vehicle_type_articulated")
    type_tanker = env.ref("deployfleet_core.vehicle_type_tanker")
    type_flatbed = env.ref("deployfleet_core.vehicle_type_flatbed")

    specs = [
        ("truck_1", "ABT 2201", "Isuzu", "FVZ 1400", type_rigid, "available", 8000.0, 9500.0, 3200.0),
        ("truck_2", "ABT 2202", "Scania", "R-Series 500", type_articulated, "available", 28000.0, 34000.0, 8500.0),
        ("truck_3", "ABT 2203", "Freightliner", "Cascadia", type_articulated, "available", 27000.0, 33000.0, 8200.0),
        ("truck_4", "ABT 2204", "Isuzu", "FVZ 1400", type_tanker, "available", 20000.0, 24000.0, 6800.0),
        ("truck_5", "ABT 2205", "Fuso", "Canter", type_flatbed, "available", 15000.0, 18000.0, 5200.0),
        ("truck_6", "ABT 2206", "Isuzu", "FVZ 1400", type_rigid, "maintenance", 8000.0, 9500.0, 3200.0),
        ("truck_7", "ABT 2207", "Scania", "R-Series 500", type_articulated, "breakdown", 28000.0, 34000.0, 8500.0),
        ("truck_8", "ABT 2208", "Freightliner", "Cascadia", type_articulated, "available", 27000.0, 33000.0, 8200.0),
    ]
    vehicles = {}
    for key, plate, brand, model_name, vehicle_type, status, max_weight, gvw, tare in specs:
        model = _get_or_create_model(env, brand, model_name)
        vehicle = vehicle_model.create({
            "license_plate": plate,
            "model_id": model.id,
            "vehicle_type_id": vehicle_type.id,
            "status": status,
            "max_weight_kg": max_weight,
            "gross_vehicle_weight_kg": gvw,
            "tare_weight_kg": tare,
            "odometer": 45000.0,
        })
        vehicles[key] = vehicle

    vehicles["truck_7"].action_set_breakdown()  # publishes deployfleet.vehicle.breakdown on the event bus
    return vehicles


def _create_drivers(env):
    employee_model = env["hr.employee"]
    specs = [
        ("driver_1", "Mulenga Chanda", "ce", "DL-ZM-100234", 9),
        ("driver_2", "Bwalya Mwansa", "c", "DL-ZM-100235", 5),
        ("driver_3", "Chileshe Banda", "ce", "DL-ZM-100236", 12),
        ("driver_4", "Mutale Phiri", "c1", "DL-ZM-100237", 3),
        ("driver_5", "Kunda Zulu", "ce", "DL-ZM-100238", 7),
        ("driver_6", "Namwene Tembo", "c", "DL-ZM-100239", 4),
        ("driver_7", "Cephas Mumba", "ce", "DL-ZM-100240", 6),
    ]
    drivers = {}
    for index, (key, name, license_class, license_number, years) in enumerate(specs):
        drivers[key] = employee_model.create({
            "name": name,
            "deployfleet_is_driver": True,
            "deployfleet_license_class": license_class,
            "deployfleet_license_number": license_number,
            "deployfleet_license_expiry": date.today() + timedelta(days=400),
            "deployfleet_years_experience": years,
            "mobile_phone": f"+26097{1234500 + index}",
        })
    return drivers


def _create_routes(env, depots):
    route_model = env["deployfleet.route"]
    specs = [
        ("Lusaka -> Ndola", depots["Lusaka HQ"], depots["Ndola"], 321.0),
        ("Lusaka -> Livingstone", depots["Lusaka HQ"], depots["Livingstone"], 475.0),
        ("Lusaka -> Kitwe", depots["Lusaka HQ"], depots["Kitwe"], 363.0),
        ("Kitwe -> Chingola", depots["Kitwe"], depots["Chingola"], 54.0),
        ("Ndola -> Kitwe", depots["Ndola"], depots["Kitwe"], 57.0),
    ]
    return {name: route_model.create({
        "name": name, "origin_depot_id": origin.id, "destination_depot_id": destination.id, "distance_km": distance,
    }) for name, origin, destination, distance in specs}


# ---------------------------------------------------------------------
# Insurance and compliance
# ---------------------------------------------------------------------

def _create_insurance_and_compliance(env, vehicles):
    policy_model = env["deployfleet.insurance.policy"]
    document_model = env["deployfleet.compliance.document"]
    roadworthiness = env.ref("deployfleet_vehicle_compliance.doc_type_vehicle_roadworthiness")
    permit = env.ref("deployfleet_vehicle_compliance.doc_type_vehicle_permit")
    registration = env.ref("deployfleet_vehicle_compliance.doc_type_vehicle_registration")
    insurer = env["res.partner"].create({"name": "Madison General Insurance Zambia", "is_company": True})

    today = date.today()
    for key, vehicle in vehicles.items():
        if key == "truck_8":
            end_date = today - timedelta(days=15)  # deliberately expired - exercises the override log
        elif key == "truck_2":
            end_date = today + timedelta(days=20)  # expiring soon - exercises the amber "expiring_soon" state
        else:
            end_date = today + timedelta(days=350)

        policy_model.create({
            "vehicle_id": vehicle.id,
            "policy_number": f"POL-{vehicle.license_plate.replace(' ', '')}",
            "insurer_id": insurer.id,
            "start_date": today - timedelta(days=365 - 350),
            "end_date": end_date,
            "premium_amount": 18500.0,
        })
        for doc_type in (roadworthiness, permit, registration):
            document_model.create({
                "document_type_id": doc_type.id,
                "res_model": "deployfleet.vehicle",
                "res_id": vehicle.id,
                "reference_number": f"{doc_type.code.upper()}-{vehicle.license_plate.replace(' ', '')}",
                "issue_date": today - timedelta(days=200),
                "expiry_date": today + timedelta(days=300),
            })


# ---------------------------------------------------------------------
# Maintenance, workshop, parts, tyres, assets
# ---------------------------------------------------------------------

def _create_maintenance_and_workshop(env, vehicles):
    schedule_model = env["deployfleet.maintenance.schedule"]
    job_card_model = env["deployfleet.workshop.job.card"]
    today = date.today()

    for key in ("truck_1", "truck_2", "truck_3", "truck_4", "truck_5"):
        vehicle = vehicles[key]
        schedule_model.create({
            "vehicle_id": vehicle.id, "name": "Oil Change", "interval_km": 10000.0,
            "last_service_odometer": vehicle.odometer - 9500.0,
        })
        schedule_model.create({
            "vehicle_id": vehicle.id, "name": "Full Service", "interval_days": 180,
            "last_service_date": today - timedelta(days=170),
        })

    closed_job_card = job_card_model.create({
        "vehicle_id": vehicles["truck_6"].id,
        "description": "Clutch replacement",
        "opened_date": today - timedelta(days=20),
    })
    closed_job_card.action_start_diagnosis()
    closed_job_card.action_start_repair()
    closed_job_card.write({
        "line_ids": [
            (0, 0, {
                "line_type": "labor", "description": "Labor - clutch replacement",
                "quantity": 6, "unit_cost": 180.0,
            }),
            (0, 0, {"line_type": "part", "description": "Clutch kit", "quantity": 1, "unit_cost": 2400.0}),
        ],
    })

    job_card_model.create({
        "vehicle_id": vehicles["truck_2"].id,
        "description": "Brake pad wear - inspection requested",
        "opened_date": today - timedelta(days=3),
    })


def _create_parts_and_tyres(env, vehicles):
    category_model = env["deployfleet.part.category"]
    part_model = env["deployfleet.part"]
    tyre_model = env["deployfleet.tyre"]

    consumables = category_model.create({"name": "Consumables"})
    tyres_category = category_model.create({"name": "Tyres"})

    part_specs = [
        ("Engine Oil Filter", "PT-OF-100", consumables, 24.0, 10.0, 85.0),
        ("Brake Pads (Set)", "PT-BP-200", consumables, 8.0, 4.0, 950.0),
        ("Clutch Kit", "PT-CK-300", consumables, 3.0, 2.0, 2400.0),
        ("Heavy Truck Tyre 315/80R22.5", "PT-TY-400", tyres_category, 6.0, 4.0, 3200.0),
    ]
    parts = {}
    for name, reference, category, qty, reorder, cost in part_specs:
        parts[reference] = part_model.create({
            "name": name, "reference": reference, "category_id": category.id,
            "quantity_on_hand": qty, "reorder_level": reorder, "unit_cost": cost,
        })

    tyre_positions = ["front_left", "front_right", "rear_left_outer", "rear_right_outer"]
    for position in tyre_positions:
        tyre_model.create({
            "vehicle_id": vehicles["truck_1"].id, "part_id": parts["PT-TY-400"].id,
            "position": position, "tread_depth_mm": 12.0,
        })


def _create_assets(env):
    asset_model = env["deployfleet.asset"]
    specs = [
        ("Flatbed Trailer #1", "trailer", "in_service"),
        ("GPS Tracker Unit #5", "gps_tracker", "in_service"),
        ("Container 40ft #2", "container", "in_storage"),
    ]
    for name, asset_type, status in specs:
        asset_model.create({"name": name, "asset_type": asset_type, "status": status})


# ---------------------------------------------------------------------
# Fuel logs (with a deliberate anomaly)
# ---------------------------------------------------------------------

def _create_fuel_logs(env, vehicles):
    fuel_log_model = env["deployfleet.fuel.log"]
    active_keys = ["truck_1", "truck_2", "truck_3", "truck_4", "truck_5", "truck_8"]
    for key in active_keys:
        vehicle = vehicles[key]
        odometer = vehicle.odometer - 4000.0
        for offset_days in (85, 68, 51, 34, 17):
            odometer += 400.0
            liters = 130.0 if not (key == "truck_3" and offset_days == 17) else 260.0  # deliberate anomaly
            fuel_log_model.create({
                "vehicle_id": vehicle.id,
                "date": date.today() - timedelta(days=offset_days),
                "odometer": odometer,
                "liters": liters,
                "total_cost": liters * 32.5,
            })


# ---------------------------------------------------------------------
# Shipments -> dispatch -> trips -> deliveries -> invoices
# ---------------------------------------------------------------------

def _create_shipment(env, customer_info, pickup, dropoff, weight_kg, pickup_days_ago, cargo):
    return env["deployfleet.shipment"].create({
        "customer_id": customer_info["partner"].id,
        "contract_id": customer_info["contract"].id,
        "pickup_depot_id": pickup.id,
        "dropoff_depot_id": dropoff.id,
        "weight_kg": weight_kg,
        "cargo_description": cargo,
        "requested_pickup_date": fields.Datetime.now() - timedelta(days=pickup_days_ago),
    })


def _assign_confirm_and_get_trip(env, shipment, vehicle, driver, route, override_reason=None):
    shipment.action_confirm()
    vals = {
        "shipment_id": shipment.id,
        "vehicle_id": vehicle.id,
        "driver_id": driver.id,
        "route_id": route.id if route else False,
        "planned_departure": shipment.requested_pickup_date,
        "planned_arrival": shipment.requested_pickup_date + timedelta(hours=8),
        "state": "proposed",
    }
    if override_reason:
        vals["compliance_override_reason"] = override_reason
    assignment = env["deployfleet.dispatch.assignment"].create(vals)
    assignment.action_confirm()
    return env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)], limit=1)


def _complete_trip_and_backdate_invoice(env, trip, invoice_month_offset):
    trip.action_depart()
    trip.action_complete(odometer_end=trip.vehicle_id.odometer + 400.0)
    invoice = env["deployfleet.invoice"].search([("trip_id", "=", trip.id)], limit=1)
    if not invoice:
        return None
    backdated = date.today().replace(day=1) - timedelta(days=1)
    for _ in range(invoice_month_offset - 1):
        backdated = backdated.replace(day=1) - timedelta(days=1)
    invoice.invoice_date = backdated.replace(day=15)
    invoice.action_confirm()
    return invoice


def _run_operations(env, customers, depots, routes, vehicles, drivers):
    customer_list = list(customers.values())

    # Completed shipments, spread across three months (each fully carried
    # through to a posted, ZRA-submission-attempted invoice) so
    # deployfleet_financial_forecast has more than one data point to draw
    # a trend line from. Not engineered to look artificially impressive -
    # a forecast built on 3 months of 1-2-2 shipments is exactly the kind
    # of thin-history output the module's own README already cautions
    # against over-trusting.
    completed_specs = [
        (customer_list[0], depots["Lusaka HQ"], depots["Ndola"], 3500.0, "Bagged sugar", "truck_1", "driver_1",
         routes["Lusaka -> Ndola"], 75, 3),
        (customer_list[1], depots["Kitwe"], depots["Chingola"], 18000.0, "Copper concentrate", "truck_4",
         "driver_2", routes["Kitwe -> Chingola"], 42, 2),
        (customer_list[2], depots["Lusaka HQ"], depots["Livingstone"], 4200.0, "Tourism supplies", "truck_2",
         "driver_3", routes["Lusaka -> Livingstone"], 40, 2),
        (customer_list[3], depots["Lusaka HQ"], depots["Kitwe"], 6000.0, "Retail goods", "truck_5", "driver_4",
         routes["Lusaka -> Kitwe"], 10, 1),
        (customer_list[4], depots["Ndola"], depots["Kitwe"], 15000.0, "Processed maize", "truck_3", "driver_5",
         routes["Ndola -> Kitwe"], 8, 1),
    ]
    for spec in completed_specs:
        customer_info, pickup, dropoff, weight, cargo, vehicle_key, driver_key, route, days_ago, month_offset = spec
        shipment = _create_shipment(env, customer_info, pickup, dropoff, weight, days_ago, cargo)
        trip = _assign_confirm_and_get_trip(env, shipment, vehicles[vehicle_key], drivers[driver_key], route)
        if trip:
            env["deployfleet.delivery"].create({
                "trip_id": trip.id, "shipment_id": shipment.id, "recipient_name": "Warehouse Supervisor",
            })
            _complete_trip_and_backdate_invoice(env, trip, month_offset)

    # One shipment on the vehicle with an expired insurance document -
    # demonstrates the compliance-override audit trail rather than being
    # silently blocked.
    override_shipment = _create_shipment(
        env, customer_list[0], depots["Lusaka HQ"], depots["Ndola"], 2000.0, 5, "Urgent spare parts run",
    )
    _assign_confirm_and_get_trip(
        env, override_shipment, vehicles["truck_8"], drivers["driver_6"], routes["Lusaka -> Ndola"],
        override_reason=(
            "No compliant vehicle available for this urgent same-day request; "
            "insurance renewal in progress."
        ),
    )

    # In-transit shipments - departed, not yet completed.
    for customer_info, pickup, dropoff, weight, cargo, vehicle_key, driver_key, route in [
        (customer_list[1], depots["Kitwe"], depots["Ndola"], 12000.0, "Mining equipment parts", "truck_2",
         "driver_7", routes["Ndola -> Kitwe"]),
    ]:
        shipment = _create_shipment(env, customer_info, pickup, dropoff, weight, 1, cargo)
        trip = _assign_confirm_and_get_trip(env, shipment, vehicles[vehicle_key], drivers[driver_key], route)
        if trip:
            trip.action_depart()

    # A still-pending shipment, not yet dispatched - shows up in the
    # dispatcher mobile app's "pending shipments" queue.
    _create_shipment(
        env, customer_list[3], depots["Lusaka HQ"], depots["Livingstone"], 5000.0, -2, "Next week's retail delivery",
    )


# ---------------------------------------------------------------------
# HR extras: leave, driver advances, load expenses, loans, performance
# ---------------------------------------------------------------------

def _create_hr_extras(env, drivers, admin):
    leave_type = env["deployfleet.leave.type"].create({"name": "Annual Leave", "default_days_per_year": 24})
    leave_model = env["deployfleet.leave.request"]

    request_1 = leave_model.create({
        "employee_id": drivers["driver_6"].id, "leave_type_id": leave_type.id,
        "date_from": date.today() + timedelta(days=30), "date_to": date.today() + timedelta(days=35),
        "reason": "Family visit",
    })
    request_1.action_submit()
    request_1.action_approve()

    request_2 = leave_model.create({
        "employee_id": drivers["driver_7"].id, "leave_type_id": leave_type.id,
        "date_from": date.today() + timedelta(days=10), "date_to": date.today() + timedelta(days=12),
    })
    request_2.action_submit()

    advance_model = env["deployfleet.driver.advance"]
    load_expense_model = env["deployfleet.load.expense"]
    advance = advance_model.create({
        "driver_id": drivers["driver_1"].id, "amount": 800.0, "purpose": "fuel",
        "issued_date": date.today() - timedelta(days=20),
    })
    # A shipment always exists by this point in the hook's own call order
    # (_run_operations runs first) - no defensive fallback needed here.
    first_shipment = env["deployfleet.shipment"].search([], limit=1, order="create_date asc")
    expense = load_expense_model.create({
        "shipment_id": first_shipment.id, "expense_type": "fuel", "amount": 750.0, "recorded_by": admin.id,
    })
    advance.reconciled_expense_ids = [(6, 0, [expense.id])]
    advance.action_mark_reconciled()

    advance_model.create({
        "driver_id": drivers["driver_2"].id, "amount": 500.0, "purpose": "subsistence",
        "issued_date": date.today() - timedelta(days=5),
    })

    env["deployfleet.loan"].create({
        "employee_id": drivers["driver_3"].id, "amount": 15000.0, "monthly_deduction": 1500.0,
        "start_date": date.today() - timedelta(days=60),
    })

    performance_model = env["deployfleet.driver.performance.event"]
    performance_model.create({
        "driver_id": drivers["driver_1"].id, "event_type": "harsh_braking",
        "date": date.today() - timedelta(days=15), "score_impact": -2.0,
        "description": "Harsh braking detected near Kabwe.",
    })
    performance_model.create({
        "driver_id": drivers["driver_5"].id, "event_type": "late_delivery",
        "date": date.today() - timedelta(days=8), "score_impact": -3.0,
        "description": "Delivery arrived 90 minutes after the planned window.",
    })


def _create_payslips(env, drivers):
    payslip_model = env["deployfleet.payroll.payslip"]
    period_end = date.today().replace(day=1) - timedelta(days=1)  # last day of the previous month
    period_start = period_end.replace(day=1)  # first day of that same month

    for driver_key, base_salary in [("driver_1", 9500.0), ("driver_3", 11000.0)]:
        payslip = payslip_model.create({
            "employee_id": drivers[driver_key].id,
            "period_start": period_start, "period_end": period_end, "base_salary": base_salary,
        })
        payslip.action_compute()
        payslip.action_confirm()


# ---------------------------------------------------------------------
# AI action requests (approval-pipeline demo, never auto-approved except
# the one deliberately taken through the full flow below)
# ---------------------------------------------------------------------

def _create_ai_action_requests(env, admin):
    request_model = env["deployfleet.ai.action.request"]
    maintenance_feature = env.ref("deployfleet_ai_agents.feature_maintenance_agent")
    vehicle_type = env.ref("deployfleet_core.vehicle_type_rigid")

    executed = request_model.create({
        "feature_id": maintenance_feature.id,
        "action_type": "create_vehicle_type",
        "target_model": "deployfleet.vehicle.type",
        "proposed_vals": '{"name": "Reefer Truck", "code": "reefer"}',
        "source_context": "scheduled_agent_run",
    })
    executed.action_submit_for_approval()
    executed.with_user(admin).action_approve()

    pending = request_model.create({
        "feature_id": maintenance_feature.id,
        "action_type": "rename_vehicle_type",
        "target_model": "deployfleet.vehicle.type",
        "target_id": vehicle_type.id,
        "proposed_vals": '{"name": "Rigid Truck (4x2)"}',
        "source_context": "dashboard_click",
    })
    pending.action_submit_for_approval()

    rejected = request_model.create({
        "feature_id": maintenance_feature.id,
        "action_type": "create_vehicle_type",
        "target_model": "deployfleet.vehicle.type",
        "proposed_vals": '{"name": "Speculative Type", "code": "speculative"}',
        "source_context": "scheduled_agent_run",
    })
    rejected.action_submit_for_approval()
    rejected.with_user(admin).action_reject(reason="Not a real vehicle category for this fleet.")


# ---------------------------------------------------------------------
# WhatsApp demo config (obviously-fake credentials, never real secrets)
# ---------------------------------------------------------------------

def _create_whatsapp_demo_config(env, company):
    env["deployfleet.ai.whatsapp.config"].create({
        "company_id": company.id,
        "phone_number_id": "DEMO-PHONE-NUMBER-ID-NOT-REAL",
        "access_token": "DEMO-ACCESS-TOKEN-NOT-REAL",
        "webhook_verify_token": "demo-verify-token-not-real",
        "enabled": False,
    })


# ---------------------------------------------------------------------
# Phase 5 crons - pre-populate predictive maintenance / fuel anomaly /
# financial forecast so the demo shows them immediately.
# ---------------------------------------------------------------------

def _run_ai_agents_crons(env):
    env["deployfleet.maintenance.prediction"]._cron_compute_all()
    env["deployfleet.fuel.anomaly"]._cron_detect_for_all_vehicles()
    env["deployfleet.financial.forecast"]._cron_compute_all_companies()
