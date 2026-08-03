/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetCard } from "../components/card/card";
import { DeployfleetAvatar } from "../components/avatar/avatar";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetAiBadge } from "../components/ai_badge/ai_badge";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";

/**
 * Internal QA/reference screen only (restricted to base.group_no_one,
 * see views/deployfleet_ui_showcase_views.xml) — not part of the
 * product's real navigation. Renders one of each component in this
 * module's first slice with its documented variants, per doc 18 §6's
 * component-contract checklist, so a human can visually verify the
 * design-system tokens and component states without a running browser
 * test harness in this repository's CI.
 */
export class DeployfleetComponentShowcase extends Component {
    static template = "deployfleet_ui.ComponentShowcase";
    static components = {
        DeployfleetButton,
        DeployfleetCard,
        DeployfleetAvatar,
        DeployfleetStatusBadge,
        DeployfleetStatusPill,
        DeployfleetAiBadge,
        DeployfleetMetricCard,
    };

    setup() {
        this.state = useState({ loadingDemo: false, pillClicks: 0 });
    }

    onLoadingDemoClick() {
        this.state.loadingDemo = true;
        setTimeout(() => {
            this.state.loadingDemo = false;
        }, 1500);
    }

    onPillClick() {
        this.state.pillClicks++;
    }
}

registry.category("actions").add("deployfleet_ui.component_showcase", DeployfleetComponentShowcase);
