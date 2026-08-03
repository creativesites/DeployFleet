/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * The base grouped-content surface. `layer` selects which of doc 17 §6's
 * two glass recipes applies — "workspace" (flat, no blur, the default)
 * or "command" (dark glass, Command Layer surfaces only). Mixing them on
 * the wrong kind of screen is doc 16's most-called-out failure mode.
 */
export class DeployfleetCard extends Component {
    static template = "deployfleet_ui.Card";
    static props = {
        layer: { type: String, optional: true },
        interactive: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        layer: "workspace",
        interactive: false,
    };

    get classes() {
        const parts = ["df-card", `df-card--${this.props.layer}`];
        if (this.props.interactive) {
            parts.push("df-card--interactive");
        }
        return parts.join(" ");
    }
}
