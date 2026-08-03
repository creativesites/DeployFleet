/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * The generic Domain Mega Menu shell (doc 16 §3.1/§7.1) — one real shared
 * component parameterized by a domain's tile list, fixing the fragility
 * DeployGuard shipped (five copy-pasted mega-menu files sharing CSS by
 * bundle-concatenation luck rather than an explicit import). Every domain
 * (Fleet & Vehicles, Dispatch & Trips, Compliance, Billing & Finance,
 * Driver & HR, AI & Intelligence) reuses this one component with its own
 * `tiles` content — see domain_content.js.
 *
 * Scope note for this slice: doc 16 describes DeployGuard's mega menu as
 * a full-screen modal overlay triggered from a persistent nav element.
 * There is no such persistent launcher yet (that's Phase B Slice 3), so
 * each domain menu is reached by direct navigation for now and renders as
 * a full Command-Layer page rather than a dismissible overlay above other
 * content. The tile grid, instant search, and Command Layer visual
 * treatment are identical either way — only "how you get here" and "how
 * you leave" change once the Launcher exists to trigger this as a modal.
 */
export class DeployfleetMegaMenu extends Component {
    static template = "deployfleet_ui.MegaMenu";
    static props = {
        label: { type: String },
        subtitle: { type: String, optional: true },
        tiles: { type: Array },
    };

    setup() {
        this.actionService = useService("action");
        this.state = useState({ searchQuery: "" });
    }

    get filteredTiles() {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) {
            return this.props.tiles;
        }
        return this.props.tiles.filter((tile) => {
            const haystack = `${tile.title} ${tile.description}`.toLowerCase();
            return haystack.includes(query);
        });
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onTileClick(tile) {
        this.actionService.doAction(tile.actionXmlId, { clearBreadcrumbs: true });
    }
}
