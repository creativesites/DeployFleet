{
    "name": "DeployFleet AI Agents",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "The six-agent catalog, plus Phase 5's advanced-intelligence slice: predictive maintenance, "
               "fuel anomaly detection, dispatch scoring, and financial forecasting",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": [
        "deployfleet_ai_core", "deployfleet_ai_permissions", "deployfleet_maintenance",
        "deployfleet_workshop", "deployfleet_fuel", "deployfleet_dispatch", "deployfleet_billing",
        "deployfleet_security", "deployfleet_compliance", "deployfleet_leave",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_ai_agent_data.xml",
        "data/deployfleet_ai_tool_data.xml",
        "data/deployfleet_ai_agents_cron.xml",
        "views/deployfleet_ai_agent_views.xml",
        "views/deployfleet_maintenance_prediction_views.xml",
        "views/deployfleet_fuel_anomaly_views.xml",
        "views/deployfleet_financial_forecast_views.xml",
    ],
}
