/** @odoo-module **/

import { Component } from "@odoo/owl";

/** Person/entity representation used across driver, dispatcher, and
 * customer-contact contexts (doc 18 §2). Falls back to initials when no
 * image is available; the status dot reuses doc 17 §2.2's status colors. */
export class DeployfleetAvatar extends Component {
    static template = "deployfleet_ui.Avatar";
    static props = {
        name: { type: String, optional: true },
        imageUrl: { type: String, optional: true },
        size: { type: String, optional: true },
        statusDot: { type: String, optional: true },
    };
    static defaultProps = {
        size: "md",
    };

    get initials() {
        if (!this.props.name) {
            return "?";
        }
        return this.props.name
            .split(" ")
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0].toUpperCase())
            .join("");
    }
}
