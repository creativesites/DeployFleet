/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DeployfleetMegaMenu } from "./mega_menu";
import { DEPLOYFLEET_MEGA_MENU_DOMAINS } from "./domain_content";

/**
 * One ir.actions.client tag, six records (one per domain, distinguished
 * only by the `params.domain` key set on each action record in
 * views/deployfleet_ui_mega_menu_views.xml) — doc 16 §3.1's "one real
 * shared OWL component parameterized by a domain's tile list, not five
 * copy-pasted files," applied to the action-registration layer too, not
 * just the presentational component.
 */
export class DeployfleetDomainMegaMenuAction extends Component {
    static template = "deployfleet_ui.DomainMegaMenuAction";
    static components = { DeployfleetMegaMenu };

    get domain() {
        const key = this.props.action?.params?.domain;
        return DEPLOYFLEET_MEGA_MENU_DOMAINS[key];
    }
}

registry.category("actions").add("deployfleet_ui.domain_mega_menu", DeployfleetDomainMegaMenuAction);
