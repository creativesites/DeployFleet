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
                actionXmlId: "deployfleet_ui.action_deployfleet_fleet_command_center",
            },
            {
                title: "Vehicle Types",
                description: "Configure the vehicle classes your fleet operates.",
                icon: "fa fa-list-alt",
                actionXmlId: "deployfleet_ui.action_deployfleet_vehicle_types_workspace",
            },
            {
                title: "Fuel Intelligence",
                description: "Fill-ups, consumption trends, and anomalies across the fleet.",
                icon: "fa fa-tint",
                actionXmlId: "deployfleet_ui.action_deployfleet_fuel_intelligence",
            },
            {
                title: "Maintenance Planner",
                description: "Attention strip, calendar, timeline, and vehicle health in one workspace.",
                icon: "fa fa-wrench",
                actionXmlId: "deployfleet_ui.action_deployfleet_maintenance_planner",
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
                actionXmlId: "deployfleet_ui.action_deployfleet_parts_registry",
            },
            {
                title: "Tyre Manager",
                description: "Tread depth, position, and replacement history across the fleet.",
                icon: "fa fa-circle-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_tyre_manager",
            },
            {
                title: "Insurance Center",
                description: "Policy renewals and claims across the fleet.",
                icon: "fa fa-shield",
                actionXmlId: "deployfleet_ui.action_deployfleet_insurance_center",
            },
            {
                title: "Assets",
                description: "Trailers, GPS units, and other non-vehicle equipment.",
                icon: "fa fa-archive",
                actionXmlId: "deployfleet_ui.action_deployfleet_asset_registry",
            },
        ],
    },
    dispatch: {
        label: "Dispatch & Trips",
        subtitle: "Shipments, assignments, and the trips that move them.",
        tiles: [
            {
                title: "Dispatch Board",
                description: "Book, assign, and track every shipment through delivery.",
                icon: "fa fa-th-large",
                actionXmlId: "deployfleet_ui.action_deployfleet_dispatch_board",
            },
            {
                title: "Trip Board",
                description: "Departures, completions, delays, and a trip calendar.",
                icon: "fa fa-road",
                actionXmlId: "deployfleet_ui.action_deployfleet_trip_board",
            },
            {
                title: "Delivery Center",
                description: "Proof of delivery across the fleet.",
                icon: "fa fa-check-square-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_delivery_center",
            },
            {
                title: "Route Manager",
                description: "The lanes your fleet runs between depots.",
                icon: "fa fa-map-signs",
                actionXmlId: "deployfleet_ui.action_deployfleet_route_manager",
            },
            {
                title: "Depot Registry",
                description: "Pickup and drop-off terminals.",
                icon: "fa fa-building",
                actionXmlId: "deployfleet_ui.action_deployfleet_depot_registry",
            },
        ],
    },
    compliance: {
        label: "Compliance",
        subtitle: "Documents, expiry tracking, and the audit trail behind every override.",
        tiles: [
            {
                title: "Compliance Center",
                description: "Every vehicle and driver, red/amber/green — who can't legally run today.",
                icon: "fa fa-th",
                actionXmlId: "deployfleet_ui.action_deployfleet_compliance_center",
            },
            {
                title: "Vehicle Documents",
                description: "Insurance, roadworthiness, permits, and registration across the fleet.",
                icon: "fa fa-file-text-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_vehicle_documents",
            },
            {
                title: "Driver Documents",
                description: "Licenses and medical certificates across the driver roster.",
                icon: "fa fa-id-card-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_driver_documents",
            },
            {
                title: "Document Types",
                description: "Configure what documents your fleet must track.",
                icon: "fa fa-list",
                actionXmlId: "deployfleet_ui.action_deployfleet_document_types_workspace",
            },
            {
                title: "Insurance Center",
                description: "Policy renewals and claims across the fleet.",
                icon: "fa fa-shield",
                actionXmlId: "deployfleet_ui.action_deployfleet_insurance_center",
            },
            {
                title: "Compliance Overrides",
                description: "The audit trail behind every non-compliant dispatch.",
                icon: "fa fa-exclamation-triangle",
                actionXmlId: "deployfleet_ui.action_deployfleet_compliance_override_ledger",
            },
        ],
    },
    billing: {
        label: "Billing & Finance",
        subtitle: "Customers, contracts, invoices, and freight cost calculations.",
        tiles: [
            {
                title: "Invoice Ledger",
                description: "Customer invoices, payment status, and ZRA submission status together.",
                icon: "fa fa-money",
                actionXmlId: "deployfleet_ui.action_deployfleet_invoice_ledger",
            },
            {
                title: "Customers",
                description: "Contracts, active shipments, and outstanding balance per customer — Customer 360.",
                icon: "fa fa-address-book",
                actionXmlId: "deployfleet_ui.action_deployfleet_customer_360",
            },
            {
                title: "Contracts & Rate Cards",
                description: "Customer contract terms and the per-trip, tonnage, distance, and lane pricing behind them.",
                icon: "fa fa-file-text-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_contract_workspace",
            },
            {
                title: "Financial Intelligence",
                description: "Revenue, outstanding balance, actual costs, and the financial forecast trend.",
                icon: "fa fa-line-chart",
                actionXmlId: "deployfleet_ui.action_deployfleet_financial_intelligence",
            },
            {
                title: "Freight Calculator",
                description: "Quick cost and profit calculations for a load.",
                icon: "fa fa-calculator",
                actionXmlId: "deployfleet_freight_calculator.action_deployfleet_freight_calculator_wizard",
            },
            {
                title: "Calculation Rules & Parameters",
                description: "The formulas and company inputs the calculator uses.",
                icon: "fa fa-sliders",
                actionXmlId: "deployfleet_ui.action_deployfleet_calculation_workspace",
            },
            {
                title: "Load Expenses",
                description: "Tolls, fuel, and other per-trip costs actually incurred.",
                icon: "fa fa-credit-card",
                actionXmlId: "deployfleet_ui.action_deployfleet_load_expense_ledger",
            },
            {
                title: "ZRA Compliance",
                description: "Smart Invoice submission status per invoice, plus device configuration status.",
                icon: "fa fa-university",
                actionXmlId: "deployfleet_ui.action_deployfleet_zra_compliance",
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
                description: "Every driver's profile, license, performance, advances, and leave — Driver 360.",
                icon: "fa fa-id-badge",
                actionXmlId: "deployfleet_ui.action_deployfleet_driver_scorecards",
            },
            {
                title: "Driver Performance",
                description: "Safety, punctuality, and incident history.",
                icon: "fa fa-line-chart",
                actionXmlId: "deployfleet_driver_performance.action_deployfleet_driver_performance_event",
            },
            {
                title: "Driver Advances",
                description: "Cash advances against upcoming pay, fleet-wide.",
                icon: "fa fa-money",
                actionXmlId: "deployfleet_ui.action_deployfleet_driver_advances",
            },
            {
                title: "Leave Planner",
                description: "Requests, who's on leave when, and balances.",
                icon: "fa fa-calendar",
                actionXmlId: "deployfleet_ui.action_deployfleet_leave_planner",
            },
            {
                title: "Payroll Center",
                description: "Payslips and loans, and the deductions that link them.",
                icon: "fa fa-file-text",
                actionXmlId: "deployfleet_ui.action_deployfleet_payroll_center",
            },
        ],
    },
    ai: {
        label: "AI & Intelligence",
        subtitle: "Predictions, suggestions, and the six-agent catalog behind them.",
        tiles: [
            {
                title: "Copilot Console",
                description: "Ask any agent a question, toggle features, and track cost.",
                icon: "fa fa-comments",
                actionXmlId: "deployfleet_ui.action_deployfleet_copilot_console",
            },
            {
                title: "Agents",
                description: "The six-agent catalog and their configuration.",
                icon: "fa fa-magic",
                actionXmlId: "deployfleet_ai_agents.action_deployfleet_ai_agent",
            },
            {
                title: "AI Predictions",
                description: "Predicted maintenance risk and statistical fuel anomalies, fleet-wide.",
                icon: "fa fa-wrench",
                actionXmlId: "deployfleet_ui.action_deployfleet_ai_predictions",
            },
            {
                title: "Financial Forecast",
                description: "Projected revenue and cost trends, alongside the real billing/AR/margin picture — Financial Intelligence.",
                icon: "fa fa-line-chart",
                actionXmlId: "deployfleet_ui.action_deployfleet_financial_intelligence",
            },
            {
                title: "AI Action History",
                description: "Every AI-proposed action, from draft through execution.",
                icon: "fa fa-check-circle-o",
                actionXmlId: "deployfleet_ui.action_deployfleet_ai_action_history",
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
