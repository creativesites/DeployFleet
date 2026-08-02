from odoo import models


class DeployfleetSequenceMixin(models.AbstractModel):
    """Shared helper for models that need a human-readable, auto-generated
    reference code (trip codes, shipment codes, dispatch batch codes, ...).

    Inheriting models call `self._deployfleet_next_reference(sequence_code)`
    from a `create()` override, rather than each module wiring up its own
    `ir.sequence` lookup boilerplate.
    """

    _name = "deployfleet.sequence.mixin"
    _description = "DeployFleet Reference Sequence Helper"

    def _deployfleet_next_reference(self, sequence_code):
        sequence = self.env["ir.sequence"].sudo()
        reference = sequence.next_by_code(sequence_code)
        if not reference:
            raise ValueError(
                f"No ir.sequence configured for code '{sequence_code}'. "
                "Add one via a data file in the module that owns this sequence."
            )
        return reference
