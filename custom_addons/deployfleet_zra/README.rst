=============================
DeployFleet ZRA Smart Invoice
=============================

Submits posted ``deployfleet.invoice`` records to the Zambia Revenue
Authority's Smart Invoice (VSDC) system automatically, triggered by the
``deployfleet.invoice.posted`` event fired by ``deployfleet_accounting``.

**Sourcing note, read before going live**: endpoint paths and request field
names (``tpin``, ``bhfId``, ``dvcSrlNo`` for device init;
``tpin``/``custTpin``/``salesTyCd``/``itemList``/etc. for sale submission)
come from ZRA's official VSDC API Specification, as reflected in the
community-maintained Postman collection at
``github.com/williemwewa/vsdc_api_postman_collection``. ZRA's own
specification PDF (``zra.org.zm``) returned HTTP 503 when this module was
written and could not be fetched directly. The response envelope shape and
the default VAT category code (``A``, standard-rated, applied to every
invoice line) are reasonable placeholders, not confirmed against a live ZRA
sandbox. **Before any production submission**: get the current spec
directly from ZRA, confirm the base URL for your registered device, and
have someone who understands ZRA's VAT category rules review
``default_vat_category_code`` and the per-line tax math in
``deployfleet.zra.client._submit_sale()`` - this module deliberately does
not attempt real VAT-inclusive/exclusive computation, since getting that
wrong on a real fiscal submission is a compliance risk, not a cosmetic bug.

``deployfleet.zra.config`` (one per company) holds the device registration;
"Initialize Device" must be run once per device before any submission will
succeed. ``deployfleet.zra.submission`` is the per-invoice submission
record and audit trail (request/response payloads, receipt number, error
message on failure) - a failed submission never raises past
``action_submit()``, it's recorded in ``error`` state for manual retry.
