/** @odoo-module **/

import { Component } from "@odoo/owl";

/** The compact, inline marker for AI-authored/AI-suggested content (doc
 * 17 §2.3, doc 18 §2). Used next to a single field, distinct from the
 * full AI Recommendation Card used for a whole suggestion. Disappears
 * once a suggestion is accepted — that behavior lives in the consuming
 * screen, not here; this component only renders the marker. */
export class DeployfleetAiBadge extends Component {
    static template = "deployfleet_ui.AiBadge";
    static props = {
        label: { type: String, optional: true },
    };
    static defaultProps = {
        label: "AI suggested",
    };
}
