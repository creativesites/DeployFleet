/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * A horizontal (vertical on narrow viewports) numbered step timeline —
 * the visual language doc 16 §7's "Learn the Business Workflow" Help
 * Center section calls for (Customer -> Contract -> Shipment -> ...).
 * New addition to doc 18 §5's signature-widget catalog.
 *
 * Deliberately data-only: `steps` is a plain array the caller already
 * loaded (typically `deployfleet.help.workflow.step` rows), not a model
 * name this component queries itself — keeps it reusable for any
 * future step-sequence, not just Help Center workflows.
 */
export class DeployfleetWorkflowDiagram extends Component {
    static template = "deployfleet_ui.WorkflowDiagram";
    static props = {
        steps: { type: Array },
        activeStepId: { type: [Number, Boolean], optional: true },
        onStepClick: { type: Function, optional: true },
    };
    static defaultProps = {
        activeStepId: false,
    };

    isActive(step) {
        return this.props.activeStepId && step.id === this.props.activeStepId;
    }

    onClickStep(step) {
        this.props.onStepClick?.(step);
    }
}
