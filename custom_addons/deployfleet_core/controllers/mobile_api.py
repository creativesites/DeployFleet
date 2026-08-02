"""Shared plumbing for every DeployFleet mobile REST controller
(deployfleet_mobile_dispatcher, deployfleet_mobile_customer, and any
future per-role mobile module) - session-cookie auth via Odoo's own
`/web/session/authenticate`, a `@require_group()` decorator for endpoint
authorization, and a single response envelope shape. Kept in
deployfleet_core (every DeployFleet module depends on it, directly or
transitively) specifically so this auth-relevant plumbing is written once
and shared, not duplicated per mobile module - see
docs/architecture/02-reuse-strategy.md §5, "keep exactly" on all three of
these.
"""

import functools

from odoo.http import request


def envelope_success(data=None):
    return {"success": True, "data": data if data is not None else {}}


def envelope_error(message):
    return {"success": False, "error": message}


def require_group(group_xml_id):
    """Decorator for a type="http" controller route returning JSON by hand:
    responds with a well-formed error envelope (never raises, never
    redirects to a login page) if the current user isn't in
    `group_xml_id`, so a mobile client always gets a parseable body."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if request.env.user._is_public() or not request.env.user.has_group(group_xml_id):
                return request.make_json_response(envelope_error("Access denied."))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_authenticated(func):
    """Same shape as `require_group()`, for routes any logged-in user may
    call regardless of group - e.g. the customer mobile app, whose users
    hold no `deployfleet_security` group at all and are instead scoped by
    ir.rule (see deployfleet_customer_portal)."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if request.env.user._is_public():
            return request.make_json_response(envelope_error("Access denied."))
        return func(*args, **kwargs)

    return wrapper
