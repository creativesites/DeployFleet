/** @odoo-module **/

import { Component } from "@odoo/owl";

/** The clickable, count-carrying variant of StatusBadge, used in
 * attention strips (doc 16 §3.3, the single most operationally valuable
 * idea adopted from DeployGuard's audit) — a count plus a label that
 * jumps to the underlying record set on click, silent when count is 0
 * (the caller decides whether to render it at all). */
export class DeployfleetStatusPill extends Component {
    static template = "deployfleet_ui.StatusPill";
    static props = {
        label: { type: String },
        count: { type: Number },
        status: { type: String },
        onClick: { type: Function, optional: true },
    };

    get classes() {
        return `df-status-pill df-status-pill--${this.props.status}`;
    }

    onClickPill(ev) {
        this.props.onClick?.(ev);
    }
}
