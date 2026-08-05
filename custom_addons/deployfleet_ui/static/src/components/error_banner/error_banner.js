/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * A generic "something went wrong loading this screen" banner.
 *
 * Engineering-audit fix (C-17): every workspace's initial onWillStart
 * data load previously had zero error handling — an AccessError from a
 * role lacking read on one model, or any other rejected query in a
 * Promise.all, left the screen's loading spinner spinning forever with
 * no way out. Every workspace's loader now catches that rejection and
 * renders this banner instead of hanging - see each screen's own
 * loader for the try/catch/finally this wraps.
 */
export class DeployfleetErrorBanner extends Component {
    static template = "deployfleet_ui.ErrorBanner";
    static props = {
        message: { type: String },
    };
}
