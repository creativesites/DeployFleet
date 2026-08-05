/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Extends Odoo's own built-in Command Palette (Ctrl+K) rather than
 * building a competing overlay bound to the same shortcut. Doc 16 §5/§6
 * calls for a global Cmd/Ctrl+K palette as "the single highest-leverage
 * click-reduction opportunity" — Odoo's web client already ships exactly
 * that surface (`@web/core/commands/command_palette_service`), so this
 * module adds DeployFleet-specific record search to it instead of
 * reimplementing the overlay, focus trap, and keyboard navigation Odoo
 * already provides and has already battle-tested.
 *
 * Typing 2+ characters searches shipment reference numbers, vehicle
 * license plates/names, and driver names; selecting a result opens that
 * record's form view directly — this is the concrete example doc 16 §5
 * describes: "today, reaching any specific record requires navigating
 * the app menu -> sub-menu -> list -> filter -> row, every time."
 */

const MIN_QUERY_LENGTH = 2;
const MAX_RESULTS_PER_MODEL = 5;

const RECORD_SEARCH_TARGETS = [
    {
        model: "deployfleet.shipment",
        kind: "Shipment",
        domain: (query) => [["name", "ilike", query]],
    },
    {
        model: "deployfleet.vehicle",
        kind: "Vehicle",
        domain: (query) => ["|", ["license_plate", "ilike", query], ["name", "ilike", query]],
    },
    {
        model: "hr.employee",
        kind: "Driver",
        domain: (query) => [["deployfleet_is_driver", "=", true], ["name", "ilike", query]],
    },
];

registry.category("command_categories").add("deployfleet", {}, { sequence: 5 });

registry.category("command_provider").add("deployfleet_ui_record_search", {
    provide: async (env, options) => {
        const query = (options.searchValue || "").trim();
        if (query.length < MIN_QUERY_LENGTH) {
            return [];
        }
        const commands = [];
        for (const target of RECORD_SEARCH_TARGETS) {
            const records = await env.services.orm.searchRead(
                target.model,
                target.domain(query),
                ["display_name"],
                { limit: MAX_RESULTS_PER_MODEL },
            );
            for (const record of records) {
                commands.push({
                    name: `${target.kind}: ${record.display_name}`,
                    category: "deployfleet",
                    action: () => {
                        env.services.action.doAction({
                            type: "ir.actions.act_window",
                            res_model: target.model,
                            res_id: record.id,
                            views: [[false, "form"]],
                            target: "current",
                        });
                    },
                });
            }
        }
        return commands;
    },
});

/**
 * Help Center article search (doc 22 §4). A separate provider block,
 * not a `RECORD_SEARCH_TARGETS` row, since it needs the backend's own
 * ranked `search_help_ids()` (title-match-first across title/summary/
 * body/tags) rather than a plain single-field `ilike` domain filter.
 *
 * Selecting a result opens the Help Center directly on that article via
 * `params.article_id` - this is this module's first use of an inline
 * `ir.actions.client` descriptor (every prior `doAction()` call in
 * deployfleet_ui either targets a stored action by xmlId or uses an
 * inline `ir.actions.act_window` descriptor, the latter already proven
 * throughout this module). It's necessary here, not just convenient:
 * articles are dynamic user content, so there is no way to pre-register
 * one stored action per article the way the six Mega Menu domains'
 * context-scoped Help Center actions do for their fixed, known set of
 * sections. The action manager resolves `{type: "ir.actions.client",
 * tag, params}` through the same standard, well-documented dispatch
 * path as any stored client action - a materially lower-risk pattern
 * than, say, patching Odoo's own NavBar DOM, which this project has
 * deliberately avoided elsewhere.
 */
registry.category("command_provider").add("deployfleet_ui_help_search", {
    provide: async (env, options) => {
        const query = (options.searchValue || "").trim();
        if (query.length < MIN_QUERY_LENGTH) {
            return [];
        }
        const ids = await env.services.orm.call(
            "deployfleet.help.article", "search_help_ids", [query], { limit: MAX_RESULTS_PER_MODEL },
        );
        if (!ids.length) {
            return [];
        }
        const records = await env.services.orm.read("deployfleet.help.article", ids, ["name"]);
        const byId = Object.fromEntries(records.map((r) => [r.id, r]));
        return ids
            .map((id) => byId[id])
            .filter(Boolean)
            .map((record) => ({
                name: `Help: ${record.name}`,
                category: "deployfleet",
                action: () => {
                    env.services.action.doAction({
                        type: "ir.actions.client",
                        tag: "deployfleet_ui.help_center",
                        params: { article_id: record.id },
                    });
                },
            }));
    },
});
