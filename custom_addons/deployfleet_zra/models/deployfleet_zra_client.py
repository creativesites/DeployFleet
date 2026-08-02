import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover — declared in __manifest__.py external_dependencies
    requests = None

_logger = logging.getLogger(__name__)


class DeployfleetZRAClient(models.AbstractModel):
    """Thin HTTP client for ZRA's Smart Invoice (VSDC) API. Endpoint paths
    and request field names below come from ZRA's official VSDC API
    Specification, as reflected in the community Postman collection at
    github.com/williemwewa/vsdc_api_postman_collection - ZRA's own PDF spec
    (zra.org.zm) returned HTTP 503 when this module was written. The
    response envelope shape (resultCd/resultMsg/data) follows the standard
    pattern used by comparable East/Southern African VSDC-style tax
    systems; no live example response was available to confirm it against
    ZRA specifically. Verify both against ZRA's sandbox before go-live.
    """

    _name = "deployfleet.zra.client"
    _description = "DeployFleet ZRA Smart Invoice HTTP Client"

    @api.model
    def _device_init(self, config):
        response = self._post(config, "/initializer/selectInitInfo", {
            "tpin": config.tpin,
            "bhfId": config.branch_id,
            "dvcSrlNo": config.device_serial_no,
        })
        data = response.get("data", {})
        config.write({
            "device_api_key": data.get("intrlKey") or data.get("apiKey") or json.dumps(data),
            "initialized": True,
        })
        return response

    @api.model
    def _submit_sale(self, config, invoice):
        payload = {
            "tpin": config.tpin,
            "bhfId": config.branch_id,
            "orgInvcNo": 0,
            "cisInvcNo": invoice.name,
            "custTpin": invoice.customer_id.vat or "",
            "custNm": invoice.customer_id.name,
            "salesTyCd": "N",
            "rcptTyCd": "S",
            "pmtTyCd": "01",
            "salesSttsCd": "02",
            "salesDt": fields.Date.to_string(invoice.invoice_date).replace("-", ""),
            "totItemCnt": len(invoice.line_ids),
            "totAmt": invoice.amount_total,
            "itemList": [
                {
                    "itemSeq": index + 1,
                    "itemCd": f"DF{line.id:010d}",
                    "itemNm": line.description,
                    "qty": line.quantity,
                    "prc": line.unit_amount,
                    "splyAmt": line.subtotal,
                    "vatCatCd": config.default_vat_category_code,
                    "totAmt": line.subtotal,
                }
                for index, line in enumerate(invoice.line_ids)
            ],
        }
        response = self._post(config, "/trnsSales/saveSales", payload)
        return payload, response

    @api.model
    def _post(self, config, path, payload):
        if not requests:
            raise UserError(self.env._(
                "The 'requests' Python package is required to call the ZRA Smart Invoice API but is not installed."
            ))
        if not config.base_url:
            raise UserError(self.env._("No ZRA API base URL configured for %s.", config.company_id.display_name))

        response = requests.post(
            f"{config.base_url.rstrip('/')}{path}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
