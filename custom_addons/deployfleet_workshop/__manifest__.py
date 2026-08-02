{
    "name": "DeployFleet Workshop",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Job cards: open -> diagnose -> repair (labor + parts) -> approve -> close",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_vehicle", "deployfleet_parts", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_workshop_sequence.xml",
        "views/deployfleet_workshop_job_card_views.xml",
    ],
}
