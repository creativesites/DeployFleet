/** @odoo-module **/

import { Component } from "@odoo/owl";

/** The platform-wide status label (doc 17 §2.2's five semantics: success,
 * warning, danger, info, ai). Purely informational — no interactive
 * states, per doc 18 §2. Use StatusPill instead where the badge needs to
 * be clickable (e.g. an attention-strip entry). */
export class DeployfleetStatusBadge extends Component {
    static template = "deployfleet_ui.StatusBadge";
    static props = {
        label: { type: String },
        status: { type: String },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        variant: "solid",
    };

    get classes() {
        return [
            "df-status-badge",
            `df-status-badge--${this.props.status}`,
            `df-status-badge--${this.props.variant}`,
        ].join(" ");
    }
}
