{
    "name": "DeployFleet UI",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Shared OWL design-system tokens and component library for DeployFleet's frontend",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["web", "deployfleet_core"],
    "data": [
        "views/deployfleet_ui_showcase_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "deployfleet_ui/static/src/scss/tokens.scss",
            "deployfleet_ui/static/src/scss/animations.scss",
            "deployfleet_ui/static/src/components/**/*.scss",
            "deployfleet_ui/static/src/components/**/*.js",
            "deployfleet_ui/static/src/components/**/*.xml",
            "deployfleet_ui/static/src/showcase/*.scss",
            "deployfleet_ui/static/src/showcase/*.js",
            "deployfleet_ui/static/src/showcase/*.xml",
        ],
    },
}
