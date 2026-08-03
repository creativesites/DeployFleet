/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";

const MODEL_TIER_LABEL = {
    cheap: "Cheap / routine",
    reasoning: "Reasoning / complex",
};

const DATA_CATEGORY_LABEL = {
    general: "General",
    payroll: "Payroll",
    financial: "Financial",
    fleet_analytics: "Fleet Analytics",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * The Copilot Console (doc 16 §7.16/§8, Phase D / Slice 1) — the
 * destination screen for working the AI investment in bulk, rather than
 * ambiently via the Copilot Rail (Phase C / Slice 4). Two real sections:
 * an **Agent Catalog** (the six `deployfleet.ai.agent` personas, each
 * with its underlying `deployfleet.ai.feature`'s live enabled/disabled
 * toggle — the per-feature switch CLAUDE.md §4 makes non-negotiable) and
 * a **Usage & Cost Dashboard** over `deployfleet.ai.usage` (this month's
 * cost/tokens via the model's own `total_cost_this_month()`, an all-time
 * cache-hit rate, a per-feature cost/token breakdown via `read_group`,
 * and a recent-calls log) — real ORM queries and a real write on
 * `enabled`, not mockup data.
 *
 * **Natural-language query interface (doc 16 §7.16/§5):** each Agent
 * Catalog card also has a real "Ask" box. Submitting a question calls
 * `deployfleet.ai.core.complete(feature.key, agent.system_prompt_template,
 * question)` — the exact same mandatory-pipeline entry point every other
 * AI feature in the product goes through (policy/permission/budget
 * checks, response cache, provider call, usage logging), not a shortcut.
 * Scoped per-agent rather than one generic global query box: each agent
 * already has its own system prompt and model tier, so "ask this agent"
 * is the more correct design than inventing a new, separate prompt/
 * routing concept for a single freeform box.
 *
 * **Scope cut, same transparency discipline as every other slice:** doc
 * 16 §7.16 also calls for each catalog entry to show "recent output" and
 * "confidence." The four Phase 5 prediction models
 * (`deployfleet.maintenance.prediction`, `deployfleet.fuel.anomaly`,
 * `deployfleet.dispatch.assignment`'s scoring, `deployfleet.financial.
 * forecast`) each use a different schema for their own risk/confidence
 * metric (e.g. `risk_score`/`risk_level` on the maintenance model) —
 * unifying that into one generic "confidence" display would need
 * per-agent custom rendering logic, not a generic read. Deferred to a
 * follow-up slice rather than built as four special cases here. Also
 * still deferred, per doc 16 §11's own Phase C/D boundary language:
 * per-record contextual awareness (the Copilot Rail/Console don't yet
 * know which record the user has open elsewhere in the app — this
 * needs a safe, verified hook into the action manager's current
 * controller, deliberately not attempted speculatively against an
 * unverified internal API, the same risk-aversion reasoning that kept
 * the Launcher off a `web.NavBar` patch).
 *
 * Command Layer treatment (light glass, per the mid-Phase-D retrofit —
 * see doc 16 Principle 1 / doc 17 §6): this is a command-center-class
 * destination screen per doc 16 §7.16's own description, the same
 * category as Mission Control, not a sustained-work Workspace screen.
 *
 * Soft-coupling: deployfleet.ai.agent/deployfleet.ai.feature/
 * deployfleet.ai.usage are referenced as plain runtime strings, the same
 * decision made throughout deployfleet_ui.
 */
export class DeployfleetCopilotConsole extends Component {
    static template = "deployfleet_ui.CopilotConsole";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetMetricCard };
    // No `static props` declaration — see the comment in
    // mission_control.js for why: this is an `ir.actions.client` root
    // component, and Odoo's action manager always injects standard
    // props (action/actionId/updateActionState/className) into it.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            agents: [],
            featureById: {},
            togglingFeatureId: null,
            costThisMonth: 0,
            tokensThisMonth: 0,
            cacheHitRate: 0,
            totalCallsAllTime: 0,
            featureBreakdown: [],
            recentCalls: [],
            questionByAgentId: {},
            answerByAgentId: {},
            askingAgentId: null,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;

        const agents = await this.orm.searchRead(
            "deployfleet.ai.agent",
            [],
            ["key", "name", "description", "related_models", "feature_id", "system_prompt_template"],
            { order: "sequence asc" },
        );
        const featureIds = agents.map((agent) => agent.feature_id[0]);
        const features = featureIds.length
            ? await this.orm.read(
                  "deployfleet.ai.feature",
                  featureIds,
                  ["key", "enabled", "model_tier", "data_category"],
              )
            : [];
        const featureById = Object.fromEntries(features.map((feature) => [feature.id, feature]));

        const [
            [costThisMonth, tokensThisMonth],
            totalCallsAllTime,
            cacheHitCallsAllTime,
            allUsageLogs,
            recentCalls,
        ] = await Promise.all([
            this.orm.call("deployfleet.ai.usage", "total_cost_this_month", []),
            this.orm.searchCount("deployfleet.ai.usage", []),
            this.orm.searchCount("deployfleet.ai.usage", [["cache_hit", "=", true]]),
            // Aggregated client-side below rather than via orm.readGroup():
            // that convenience method doesn't exist on this exact Odoo 19
            // nightly's ORM service ("this.orm.readGroup is not a
            // function") - the same class of version-drift already hit
            // elsewhere in this project. searchRead + a plain JS reduce
            // avoids depending on an unverified internal method name.
            this.orm.searchRead(
                "deployfleet.ai.usage",
                [],
                ["feature", "estimated_cost_usd", "tokens_in", "tokens_out"],
                { limit: 2000 },
            ),
            this.orm.searchRead(
                "deployfleet.ai.usage",
                [],
                ["feature", "provider", "tokens_in", "tokens_out", "estimated_cost_usd", "cache_hit", "call_date", "state"],
                { order: "call_date desc", limit: 10 },
            ),
        ]);

        const breakdownByFeature = {};
        for (const log of allUsageLogs) {
            const row = (breakdownByFeature[log.feature] ??= {
                feature: log.feature,
                __count: 0,
                estimated_cost_usd: 0,
                tokens_in: 0,
                tokens_out: 0,
            });
            row.__count += 1;
            row.estimated_cost_usd += log.estimated_cost_usd;
            row.tokens_in += log.tokens_in;
            row.tokens_out += log.tokens_out;
        }
        const featureBreakdown = Object.values(breakdownByFeature).sort(
            (a, b) => b.estimated_cost_usd - a.estimated_cost_usd,
        );

        this.state.agents = agents;
        this.state.featureById = featureById;
        this.state.costThisMonth = costThisMonth;
        this.state.tokensThisMonth = tokensThisMonth;
        this.state.totalCallsAllTime = totalCallsAllTime;
        this.state.cacheHitRate = totalCallsAllTime > 0 ? (cacheHitCallsAllTime / totalCallsAllTime) * 100 : 0;
        this.state.featureBreakdown = featureBreakdown;
        this.state.recentCalls = recentCalls;
        this.state.loading = false;
    }

    modelTierLabel(tier) {
        return MODEL_TIER_LABEL[tier] || tier;
    }

    dataCategoryLabel(category) {
        return DATA_CATEGORY_LABEL[category] || category;
    }

    relatedModelsList(relatedModels) {
        return relatedModels ? relatedModels.split(",").map((entry) => entry.trim()).filter(Boolean) : [];
    }

    get formattedCostThisMonth() {
        return this.state.costThisMonth.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    get formattedTokensThisMonth() {
        return this.state.tokensThisMonth.toLocaleString();
    }

    get formattedCacheHitRate() {
        return `${this.state.cacheHitRate.toFixed(1)}%`;
    }

    onQuestionInput(agentId, ev) {
        this.state.questionByAgentId[agentId] = ev.target.value;
    }

    async onAskAgent(agent) {
        const question = (this.state.questionByAgentId[agent.id] || "").trim();
        if (!question) {
            return;
        }
        const feature = this.state.featureById[agent.feature_id[0]];
        this.state.askingAgentId = agent.id;
        this.state.answerByAgentId[agent.id] = null;
        try {
            const answer = await this.orm.call("deployfleet.ai.core", "complete", [
                feature.key,
                agent.system_prompt_template,
                question,
            ]);
            this.state.answerByAgentId[agent.id] = answer;
            // The call itself already logged to deployfleet.ai.usage - the
            // dashboard above will reflect it next time this screen loads,
            // deliberately not force-refreshed here to avoid flashing the
            // whole screen back to its loading state right after an answer
            // renders.
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.askingAgentId = null;
        }
    }

    async onToggleFeature(featureId) {
        const feature = this.state.featureById[featureId];
        if (!feature) {
            return;
        }
        this.state.togglingFeatureId = featureId;
        try {
            await this.orm.write("deployfleet.ai.feature", [featureId], { enabled: !feature.enabled });
            feature.enabled = !feature.enabled;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.togglingFeatureId = null;
        }
    }
}

registry.category("actions").add("deployfleet_ui.copilot_console", DeployfleetCopilotConsole);
