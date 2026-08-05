/** @odoo-module **/

import { onWillUnmount, reactive } from "@odoo/owl";

/**
 * Shared reactive "what should the Help Trigger open to" store — the
 * structural twin of `copilot_rail/copilot_context.js`, doc 22 §4's
 * ambient (tier 1) contextual-help mechanism. A workspace opts in with
 * one `setup()` line; the persistent Help Trigger reads this to decide
 * whether clicking it opens the Help Center on a specific topic or on
 * the plain home landing page. Populated only by an explicit, opt-in
 * call from a workspace component — never inferred from the action
 * manager's internals, the same risk-aversion already applied to the
 * Launcher and to `copilotContextStore`.
 *
 * Deliberately just a `contextKey`/`label` pair, not a full record
 * pointer like `copilotContextStore` - the Help Trigger navigates to a
 * Help Center *topic*, it doesn't need to know which specific vehicle/
 * shipment/driver record the user has open, only which workspace they're
 * in.
 */
export const helpContextStore = reactive({
    contextKey: null,
    label: null,
});

function isCurrent(contextKey) {
    return helpContextStore.contextKey === contextKey;
}

/**
 * Call once from a workspace component's `setup()`. Returns
 * `{ setContext, clearContext }` for that component to call
 * imperatively — matching `useCopilotContext()`'s own imperative (not
 * reactive-effect-driven) design. Automatically clears the shared store
 * on unmount if this component's own context is still the one showing.
 */
export function useHelpContext() {
    let ownContextKey = null;

    function setContext(contextKey, label) {
        ownContextKey = contextKey;
        Object.assign(helpContextStore, { contextKey, label });
    }

    function clearContext() {
        if (isCurrent(ownContextKey)) {
            Object.assign(helpContextStore, { contextKey: null, label: null });
        }
        ownContextKey = null;
    }

    onWillUnmount(clearContext);

    return { setContext, clearContext };
}
