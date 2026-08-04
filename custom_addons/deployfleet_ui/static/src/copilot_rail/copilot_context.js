/** @odoo-module **/

import { onWillUnmount, reactive } from "@odoo/owl";

/**
 * Shared reactive "what is the user currently looking at" store (doc 21
 * §2 — docs/architecture/21-copilot-rail-architecture.md). The Copilot
 * Rail reads this to show a context chip and fold a line into the Chat
 * prompt. Populated only by an explicit, opt-in call from a workspace
 * component — never by hooking into Odoo's action-manager internals, the
 * same risk-aversion already applied twice to the Launcher (doc 16 §3.2's
 * deliberate scope correction away from patching `web.NavBar`, since a
 * bad match against this exact Odoo 19 nightly's internal template
 * structure could break navigation product-wide). A screen that never
 * calls useCopilotContext() simply leaves the Rail with no context to
 * show — nothing else depends on this being populated.
 */
export const copilotContextStore = reactive({
    domain: null,
    model: null,
    recordId: null,
    recordLabel: null,
});

function isCurrent(model, recordId) {
    return copilotContextStore.model === model && copilotContextStore.recordId === recordId;
}

/**
 * Call once from a workspace component's setup(). Returns
 * `{ setContext, clearContext }` for that component to call imperatively
 * whenever the record the user is focused on changes (e.g. expanding a
 * different card) — deliberately imperative rather than reactive-effect-
 * driven, matching how these workspaces already manage their own
 * useState rather than OWL effects. Automatically clears the shared
 * store on unmount if this component's own context is still the one
 * showing, so the Rail never displays a stale "looking at X" after the
 * user navigates away.
 */
export function useCopilotContext() {
    let ownModel = null;
    let ownRecordId = null;

    function setContext({ domain, model, recordId, recordLabel }) {
        ownModel = model;
        ownRecordId = recordId;
        Object.assign(copilotContextStore, { domain, model, recordId, recordLabel });
    }

    function clearContext() {
        if (isCurrent(ownModel, ownRecordId)) {
            Object.assign(copilotContextStore, { domain: null, model: null, recordId: null, recordLabel: null });
        }
        ownModel = null;
        ownRecordId = null;
    }

    onWillUnmount(clearContext);

    return { setContext, clearContext };
}
