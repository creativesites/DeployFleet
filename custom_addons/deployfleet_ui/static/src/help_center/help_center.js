/** @odoo-module **/

import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetCard } from "../components/card/card";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetWorkflowDiagram } from "../components/workflow_diagram/workflow_diagram";
import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

// The Help Center landing page's fixed card set (doc 22 §1's ten
// sections, minus Interactive Walkthroughs/Video Support, which are
// documented as future work, not built - see doc 22 §7). Each card
// navigates via a stable category `slug`, not a database id, since
// slugs are what the seed data and any future content author can rely
// on staying constant.
const HOME_CARDS = [
    {
        key: "getting-started", icon: "fa fa-compass", title: "Getting Started",
        description: "Log in, find your way around, and learn the basics in a few minutes.",
    },
    {
        key: "business-workflows", icon: "fa fa-random", title: "Learn the Business Workflow",
        description: "See how a shipment, a vehicle, and a driver actually move through DeployFleet.",
    },
    {
        key: "module-guides", icon: "fa fa-book", title: "Module Guides",
        description: "A plain-language guide to every part of DeployFleet.",
    },
    {
        key: "faq", icon: "fa fa-question-circle", title: "FAQ",
        description: "Quick answers to common questions.",
    },
    {
        key: "troubleshooting", icon: "fa fa-life-ring", title: "Troubleshooting",
        description: "Something not working the way you expect? Start here.",
    },
    {
        key: "ai-copilot-help", icon: "fa fa-magic", title: "AI Copilot Help",
        description: "What Copilot can do, and how to ask it for help.",
    },
];

const CONTENT_TYPE_LABELS = {
    guide: "Guide", module_guide: "Module Guide", faq: "FAQ", troubleshooting: "Troubleshooting",
};

const ARTICLE_FIELDS = [
    "name", "summary", "body", "content_type", "category_id", "tag_ids",
    "related_article_ids", "related_workflow_id", "sequence",
];

/**
 * The DeployFleet Help Center (doc 22) - a single workspace with an
 * internal `state.activeSection` router, the same "one action, many
 * sections" pattern already used by Compliance Center / Copilot
 * Console, rather than one `ir.actions.client` per section.
 *
 * `home` is a Command Layer landing surface (doc 16 Principle 1 - an
 * orientation screen, not sustained work); once a user drills into a
 * category or article it switches to Workspace Layer (flat, no blur) -
 * a deliberate in-screen exception, the same class already granted to
 * the Dispatch Board.
 *
 * Content models (`deployfleet.help.*`) are referenced as plain runtime
 * strings, the same soft-coupling decision made throughout
 * deployfleet_ui - deployfleet_help is not a manifest dependency.
 *
 * Contextual deep-linking: `props.action.params.article_id`, when set
 * (the Command Palette's Help results - see
 * command_palette/deployfleet_command_provider.js - know the exact
 * article a search matched, so they skip context-key resolution
 * entirely and open it directly) wins outright. Otherwise
 * `props.action.params.context_key` (set by a Mega Menu Help tile or a
 * workspace's "Help" button, see fleet_command_center.js/
 * workshop_board.js/payroll_center.js) is resolved in this order -
 * (1) an article whose own `context_key` matches wins, (2) else a
 * category whose `context_key` matches, (3) else a category whose
 * `domain_key` matches, (4) else the Help Center opens on `home`. This
 * is doc 22 §3's resolution algorithm.
 */
export class DeployfleetHelpCenter extends Component {
    static template = "deployfleet_ui.HelpCenter";
    static components = {
        DeployfleetButton, DeployfleetCard, DeployfleetStatusBadge, DeployfleetWorkflowDiagram, DeployfleetErrorBanner,
    };
    // No `static props` declaration, deliberately - see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component and Odoo's action manager injects standard props.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.homeCards = HOME_CARDS;
        this.state = useState({
            loading: true,
            loadError: null,
            activeSection: "home",
            categories: [],
            workflows: [],
            sectionArticles: [],
            sectionCategory: null,
            article: null,
            workflowDetail: null,
            expandedArticleId: null,
            searchQuery: "",
            searchResults: [],
            searching: false,
        });

        onWillStart(() => this.loadInitial());
    }

    async loadInitial() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const [categories, workflows] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.help.category",
                    [],
                    ["name", "slug", "parent_id", "icon", "description", "domain_key", "context_key", "sequence"],
                    { order: "sequence, name" },
                ),
                this.orm.searchRead(
                    "deployfleet.help.workflow",
                    [],
                    ["name", "slug", "description", "domain_key"],
                    { order: "sequence, name" },
                ),
            ]);
            this.state.categories = categories;
            this.state.workflows = workflows;
            await this.resolveContext();
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async resolveContext() {
        const articleId = this.props.action?.params?.article_id;
        if (articleId) {
            await this.openArticle(articleId);
            return;
        }
        const contextKey = this.props.action?.params?.context_key;
        if (!contextKey) {
            return;
        }
        const [articleMatch] = await this.orm.searchRead(
            "deployfleet.help.article", [["context_key", "=", contextKey]], ["id"], { limit: 1 },
        );
        if (articleMatch) {
            await this.openArticle(articleMatch.id);
            return;
        }
        let category = this.state.categories.find((c) => c.context_key === contextKey);
        if (!category) {
            category = this.state.categories.find((c) => c.domain_key === contextKey);
        }
        if (category) {
            await this.openCategory(category);
        }
    }

    contentTypeLabel(type) {
        return CONTENT_TYPE_LABELS[type] || type;
    }

    categoryBySlug(slug) {
        return this.state.categories.find((c) => c.slug === slug);
    }

    get moduleGuideCategories() {
        const parent = this.categoryBySlug("module-guides");
        if (!parent) {
            return [];
        }
        return this.state.categories.filter((c) => c.parent_id && c.parent_id[0] === parent.id);
    }

    async onHomeCardClick(cardKey) {
        const category = this.categoryBySlug(cardKey);
        if (category) {
            await this.openCategory(category);
        }
    }

    /**
     * A category with exactly one article (Getting Started, AI Copilot
     * Help, and every individual Module Guide child reached via a
     * contextual deep-link) opens that article directly rather than a
     * one-item list. "Module Guides" and "Learn the Business Workflow"
     * are special-cased to their own richer sections.
     */
    async openCategory(category) {
        this.state.loadError = null;
        if (category.slug === "business-workflows") {
            this.state.activeSection = "workflows";
            return;
        }
        if (category.slug === "module-guides") {
            await this.loadGuides();
            return;
        }
        try {
            const articles = await this.orm.searchRead(
                "deployfleet.help.article",
                [["category_id", "=", category.id]],
                ["name", "summary", "content_type", "sequence"],
                { order: "sequence, name" },
            );
            if (articles.length === 1) {
                await this.openArticle(articles[0].id);
                return;
            }
            this.state.sectionCategory = category;
            this.state.sectionArticles = articles;
            this.state.expandedArticleId = null;
            this.state.activeSection = "category";
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        }
    }

    async loadGuides() {
        try {
            const articles = await this.orm.searchRead(
                "deployfleet.help.article",
                [["content_type", "=", "module_guide"]],
                ["name", "summary", "category_id", "sequence"],
                { order: "sequence, name" },
            );
            this.state.sectionArticles = articles;
            this.state.activeSection = "guides";
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        }
    }

    onToggleArticleInList(articleId) {
        this.state.expandedArticleId = this.state.expandedArticleId === articleId ? null : articleId;
    }

    async openArticle(articleId) {
        this.state.loadError = null;
        try {
            const [article] = await this.orm.read("deployfleet.help.article", [articleId], ARTICLE_FIELDS);
            article.relatedArticles = article.related_article_ids.length
                ? await this.orm.read("deployfleet.help.article", article.related_article_ids, ["name"])
                : [];
            this.state.article = article;
            this.state.activeSection = "article";
            // Fire-and-forget: a view-count bump must never block the
            // reading experience if it fails.
            this.orm.call("deployfleet.help.article", "action_register_view", [[articleId]]).catch(() => {});
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        }
    }

    async openWorkflow(workflowId) {
        this.state.loadError = null;
        try {
            const [workflow] = await this.orm.read(
                "deployfleet.help.workflow", [workflowId], ["name", "description"],
            );
            const steps = await this.orm.searchRead(
                "deployfleet.help.workflow.step",
                [["workflow_id", "=", workflowId]],
                ["title", "description", "icon", "related_model", "related_article_id"],
                { order: "sequence" },
            );
            this.state.workflowDetail = { ...workflow, steps };
            this.state.activeSection = "workflow_detail";
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        }
    }

    /**
     * `body` is `fields.Html(sanitize=True)` - already sanitized
     * server-side on write, so marking it as trusted markup here (the
     * standard OWL 2 mechanism for rendering HTML-safe content via
     * `t-out`) is the correct, minimal-risk way to render it, the same
     * way Odoo's own Html field widget does. The first place this
     * codebase renders a Html-field value in an OWL template.
     */
    get articleBodyMarkup() {
        return markup(this.state.article?.body || "");
    }

    onStepClick(step) {
        if (step.related_article_id) {
            this.openArticle(step.related_article_id[0]);
        }
    }

    goHome() {
        this.state.activeSection = "home";
        this.state.article = null;
        this.state.workflowDetail = null;
        this.state.sectionCategory = null;
        this.state.searchQuery = "";
        this.state.searchResults = [];
    }

    async onSearchInput(value) {
        this.state.searchQuery = value;
        if (!value || value.trim().length < 2) {
            this.state.searchResults = [];
            this.state.activeSection = this.state.activeSection === "search" ? "home" : this.state.activeSection;
            return;
        }
        this.state.searching = true;
        this.state.activeSection = "search";
        try {
            const results = await this.orm.call(
                "deployfleet.help.article", "search_help_ids", [value], { limit: 20 },
            );
            const [records] = await Promise.all([
                results.length
                    ? this.orm.read(
                        "deployfleet.help.article", results, ["name", "summary", "content_type", "category_id"],
                    )
                    : Promise.resolve([]),
            ]);
            // search_help_ids() already returns ids ranked title-first;
            // read() does not preserve that order, so re-sort by the
            // ranked id list.
            const byId = Object.fromEntries(records.map((r) => [r.id, r]));
            this.state.searchResults = results.map((id) => byId[id]).filter(Boolean);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.searching = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.help_center", DeployfleetHelpCenter);
