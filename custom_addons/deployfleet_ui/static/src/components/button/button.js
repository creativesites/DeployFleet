/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * The one Button implementation for the whole product (doc 18 §2). No
 * module should ship its own button markup — extend this component's
 * variants instead.
 */
export class DeployfleetButton extends Component {
    static template = "deployfleet_ui.Button";
    static props = {
        label: { type: String, optional: true },
        variant: { type: String, optional: true },
        icon: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        loading: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        variant: "secondary",
        disabled: false,
        loading: false,
    };

    get classes() {
        const parts = ["df-button", `df-button--${this.props.variant}`];
        if (this.props.disabled || this.props.loading) {
            parts.push("df-button--disabled");
        }
        return parts.join(" ");
    }

    onClickButton(ev) {
        if (this.props.disabled || this.props.loading) {
            return;
        }
        this.props.onClick?.(ev);
    }
}
