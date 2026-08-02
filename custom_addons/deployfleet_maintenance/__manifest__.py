{
    "name": "DeployFleet Maintenance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Odometer/calendar preventive service scheduling, publishes deployfleet.maintenance.due",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_vehicle", "deployfleet_workshop", "deployfleet_event_bus"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_maintenance_cron.xml",
        "views/deployfleet_maintenance_schedule_views.xml",
    ],
}
