/** @odoo-module **/

/**
 * Curated tile content per operational domain (doc 16 §3.1/§5), grounded
 * in the actual 65-menu-item inventory across all 43 backend modules —
 * not invented placeholder content. This is a deliberate curation of
 * each domain's main workflow screens, not a mechanical dump of every
 * menu item in the product: admin/config-only screens (AI provider
 * config/budget/usage log, notification rules, the event bus, mobile
 * device registrations, licenses) stay reachable through the standard
 * menu for now rather than being promoted into a mega-menu tile — the
 * same "ship the important workflows first" judgment call
 * 09-dispatch-module-design.md made for the Dispatch Board itself.
 */
export const DEPLOYFLEET_MEGA_MENU_DOMAINS = {
    fleet: {
        label: "Fleet & Vehicles",
        subtitle: "Vehicles, maintenance, fuel, and everything that keeps the trucks running.",
        tiles: [
            {
                title: "Vehicles",
                description: "Every vehicle's profile, status, and compliance at a glance.",
                icon: "fa fa-truck",
                actionXmlId: "deployfleet_vehicle.action_deployfleet_vehicle",
            },
            {
                title: "Vehicle Types",
                description: "Configure the vehicle classes your fleet operates.",
                icon: "fa fa-list-alt",
                actionXmlId: "deployfleet_core.action_deployfleet_vehicle_type",
            },
            {
                title: "Fuel Logs",
                description: "Fill-ups, cost per litre, and consumption trends.",
                icon: "fa fa-tint",
                actionXmlId: "deployfleet_fuel.action_deployfleet_fuel_log",
            },
            {
                title: "Maintenance",
                description: "Scheduled service intervals and what's coming due.",
                icon: "fa fa-wrench",
                actionXmlId: "deployfleet_maintenance.action_deployfleet_maintenance_schedule",
            },
            {
                title: "Workshop",
                description: "Job cards from diagnosis through to repair complete.",
                icon: "fa fa-cogs",
                actionXmlId: "deployfleet_ui.action_deployfleet_workshop_board",
            },
            {
                title: "Parts",
                description: "Inventory, categories, and reorder levels.",
                icon: "fa fa-cubes",
                actionXmlId: "deployfleet_parts.action_deployfleet_part",
            },
            {
                title: "Tyres",
                description: "Tread depth and position tracking per vehicle.",
                icon: "fa fa-circle-o",
                actionXmlId: "deployfleet_tyres.action_deployfleet_tyre",
            },
            {
                title: "Assets",
                description: "Trailers, GPS units, and other non-vehicle equipment.",
                icon: "fa fa-archive",
                actionXmlId: "deployfleet_assets.action_deployfleet_asset",
            },
        ],
    },
    dispatch: {
        label: "Dispatch & Trips",
        subtitle: "Shipments, assignments, and the trips that move them.",
        tiles: [
            {
                title: "Shipments",
                description: "Every customer shipment from booking to delivery.",
                icon: "fa fa-cube",
                actionXmlId: "deployfleet_dispatch.action_deployfleet_shipment",
            },
            {
                title: "Dispatch Board",
                description: "Assign drivers and vehicles to today's shipments.",
                icon: "fa fa-th-large",
                actionXmlId: "deployfleet_dispatch.action_deployfleet_dispatch_assignment",
            },
            {
                title: "Trips",
                description: "Departed, in-transit, and completed trips.",
                icon: "fa fa-road",
                actionXmlId: "deployfleet_trip.action_deployfleet_trip",
            },
            {
                title: "Deliveries",
                description: "Proof of delivery and completion records.",
                icon: "fa fa-check-square-o",
                actionXmlId: "deployfleet_delivery.action_deployfleet_delivery",
            },
            {
                title: "Routes",
                description: "The lanes your fleet runs between depots.",
                icon: "fa fa-map-signs",
                actionXmlId: "deployfleet_route.action_deployfleet_route",
            },
            {
                title: "Depots",
                description: "Pickup and dropoff terminals.",
                icon: "fa fa-building",
                actionXmlId: "deployfleet_customer.action_deployfleet_depot",
            },
        ],
    },
    compliance: {
        label: "Compliance",
        subtitle: "Documents, expiry tracking, and the audit trail behind every override.",
        tiles: [
            {
                title: "Documents",
                description: "Every compliance document and its expiry status.",
                icon: "fa fa-file-text-o",
                actionXmlId: "deployfleet_compliance.action_deployfleet_compliance_document",
            },
            {
                title: "Document Types",
                description: "Configure what documents your fleet must track.",
                icon: "fa fa-list",
                actionXmlId: "deployfleet_compliance.action_deployfleet_compliance_document_type",
            },
            {
                title: "Insurance",
                description: "Vehicle insurance policies and coverage periods.",
                icon: "fa fa-shield",
                actionXmlId: "deployfleet_insurance.action_deployfleet_insurance_policy",
            },
            {
                title: "Compliance Overrides",
                description: "The audit trail behind every non-compliant dispatch.",
                icon: "fa fa-exclamation-triangle",
                actionXmlId: "deployfleet_dispatch_compliance.action_deployfleet_dispatch_compliance_override_log",
            },
        ],
    },
    billing: {
        label: "Billing & Finance",
        subtitle: "Contracts, rate cards, invoices, and freight cost calculations.",
        tiles: [
            {
                title: "Invoices",
                description: "Customer invoices and payment status.",
                icon: "fa fa-money",
                actionXmlId: "deployfleet_billing.action_deployfleet_invoice",
            },
            {
                title: "Rate Cards",
                description: "Per-trip, tonnage, distance, and lane pricing rules.",
                icon: "fa fa-percent",
                actionXmlId: "deployfleet_billing.action_deployfleet_rate_card",
            },
            {
                title: "Contracts",
                description: "Customer contract terms and billing plans.",
                icon: "fa fa-file-text-o",
                actionXmlId: "deployfleet_customer.action_deployfleet_contract",
            },
            {
                title: "Freight Calculator",
                description: "Quick cost and profit calculations for a load.",
                icon: "fa fa-calculator",
                actionXmlId: "deployfleet_freight_calculator.action_deployfleet_freight_calculator_wizard",
            },
            {
                title: "Calculation Rules",
                description: "Configure the formulas the calculator uses.",
                icon: "fa fa-sliders",
                actionXmlId: "deployfleet_freight_calculator.action_deployfleet_calculation_rule",
            },
            {
                title: "Load Expenses",
                description: "Tolls, fuel, and other per-trip costs.",
                icon: "fa fa-credit-card",
                actionXmlId: "deployfleet_load_expense.action_deployfleet_load_expense",
            },
            {
                title: "ZRA Submissions",
                description: "Smart Invoice submission status per invoice.",
                icon: "fa fa-university",
                actionXmlId: "deployfleet_zra.action_deployfleet_zra_submission",
            },
            {
                title: "Client Summary Report",
                description: "A shareable summary of a customer's activity.",
                icon: "fa fa-bar-chart",
                actionXmlId: "deployfleet_client_reports.action_deployfleet_client_report_wizard",
            },
        ],
    },
    driver: {
        label: "Driver & HR",
        subtitle: "Everyone behind the wheel, and everything owed to them.",
        tiles: [
            {
                title: "Drivers",
                description: "Every driver's profile and current status.",
                icon: "fa fa-id-badge",
                actionXmlId: "deployfleet_driver.action_deployfleet_driver",
            },
            {
                title: "Driver Performance",
                description: "Safety, punctuality, and incident history.",
                icon: "fa fa-line-chart",
                actionXmlId: "deployfleet_driver_performance.action_deployfleet_driver_performance_event",
            },
            {
                title: "Driver Advances",
                description: "Cash advances against upcoming pay.",
                icon: "fa fa-money",
                actionXmlId: "deployfleet_driver_advance.action_deployfleet_driver_advance",
            },
            {
                title: "Leave",
                description: "Leave requests and approvals.",
                icon: "fa fa-calendar",
                actionXmlId: "deployfleet_leave.action_deployfleet_leave_request",
            },
            {
                title: "Payslips",
                description: "Computed and confirmed payroll runs.",
                icon: "fa fa-file-text",
                actionXmlId: "deployfleet_payroll.action_deployfleet_payroll_payslip",
            },
            {
                title: "Loans",
                description: "Employee loans and repayment schedules.",
                icon: "fa fa-bank",
                actionXmlId: "deployfleet_loans.action_deployfleet_loan",
            },
        ],
    },
    ai: {
        label: "AI & Intelligence",
        subtitle: "Predictions, suggestions, and the six-agent catalog behind them.",
        tiles: [
            {
                title: "Agents",
                description: "The six-agent catalog and their configuration.",
                icon: "fa fa-magic",
                actionXmlId: "deployfleet_ai_agents.action_deployfleet_ai_agent",
            },
            {
                title: "Predictive Maintenance",
                description: "Which vehicles are predicted to need service soon.",
                icon: "fa fa-wrench",
                actionXmlId: "deployfleet_ai_agents.action_deployfleet_maintenance_prediction",
            },
            {
                title: "Fuel Anomalies",
                description: "Fill-ups that look statistically unusual.",
                icon: "fa fa-exclamation-circle",
                actionXmlId: "deployfleet_ai_agents.action_deployfleet_fuel_anomaly",
            },
            {
                title: "Financial Forecast",
                description: "Projected revenue and cost trends.",
                icon: "fa fa-line-chart",
                actionXmlId: "deployfleet_ai_agents.action_deployfleet_financial_forecast",
            },
            {
                title: "Action Requests",
                description: "The approval queue for every AI-suggested action.",
                icon: "fa fa-check-circle-o",
                actionXmlId: "deployfleet_ai_actions.action_deployfleet_ai_action_request",
            },
            {
                title: "Permissions",
                description: "Which roles may use which AI features.",
                icon: "fa fa-lock",
                actionXmlId: "deployfleet_ai_permissions.action_deployfleet_ai_permission",
            },
            {
                title: "WhatsApp",
                description: "The WhatsApp channel configuration for AI conversations.",
                icon: "fa fa-whatsapp",
                actionXmlId: "deployfleet_ai_whatsapp.action_deployfleet_ai_whatsapp_config",
            },
        ],
    },
};
