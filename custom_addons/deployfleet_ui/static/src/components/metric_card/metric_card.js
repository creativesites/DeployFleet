/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * The standardized KPI card (doc 16 §3.4, doc 18 §3) — replaces the five
 * inconsistent hand-rolled variants found across DeployGuard's own
 * dashboards. Left-border-stripe status color, one large value, an
 * optional trend indicator. The trend's "good"/"bad" direction must be
 * decided explicitly by the caller per metric (doc 17 §2.2's
 * business-meaning-override rule) — this component never assumes
 * "up = green".
 */
export class DeployfleetMetricCard extends Component {
    static template = "deployfleet_ui.MetricCard";
    static props = {
        label: { type: String },
        value: { type: [String, Number] },
        icon: { type: String, optional: true },
        status: { type: String, optional: true },
        caption: { type: String, optional: true },
        trend: { type: Object, optional: true },
        onClick: { type: Function, optional: true },
    };
    static defaultProps = {
        status: "info",
    };

    get classes() {
        const parts = ["df-metric-card", `df-metric-card--${this.props.status}`];
        if (this.props.onClick) {
            parts.push("df-metric-card--clickable");
        }
        return parts.join(" ");
    }

    get trendClasses() {
        if (!this.props.trend) {
            return "";
        }
        return `df-metric-card__trend df-metric-card__trend--${this.props.trend.isGood ? "good" : "bad"}`;
    }

    onClickCard(ev) {
        this.props.onClick?.(ev);
    }
}
