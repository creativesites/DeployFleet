/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DeployfleetAiBadge } from "../ai_badge/ai_badge";
import { DeployfleetButton } from "../button/button";

/**
 * The full ambient-AI suggestion surface (doc 16 §6/§8, doc 18 §2, Phase
 * D) — distinct from `AiBadge`'s inline single-field marker, this is for
 * a whole AI-generated suggestion/insight sitting inline on a flagship
 * screen (e.g. a predictive-maintenance risk alongside a vehicle's
 * detail). Never auto-applies anything itself: `onAction` is the
 * caller's own handler, and every consumer of this component must route
 * any resulting write through the mandatory suggestion -> approval ->
 * execute -> audit pipeline ([08-ai-architecture.md](../../../../../../docs/architecture/08-ai-architecture.md)
 * §5) — this component only renders the suggestion, it never writes
 * anything on its own.
 */
export class DeployfleetAiRecommendationCard extends Component {
    static template = "deployfleet_ui.AiRecommendationCard";
    static components = { DeployfleetAiBadge, DeployfleetButton };
    static props = {
        title: { type: String },
        body: { type: String },
        meta: { type: String, optional: true },
        actionLabel: { type: String, optional: true },
        onAction: { type: Function, optional: true },
        onDismiss: { type: Function, optional: true },
    };
}
