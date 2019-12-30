# Copyright 2013 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2014 Markus Schneider <markus.schneider@initos.com>
# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from operator import itemgetter

from odoo import _, api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.move"

    returned_payment = fields.Boolean(
        string="Payment returned",
        help="Invoice has been included on a payment that has been returned later.",
    )

    def check_payment_return(self):
        returned_invoices = (
            self.env["account.partial.reconcile"]
            .search([("origin_returned_move_ids.move_id", "in", self.ids)])
            .mapped("origin_returned_move_ids.move_id")
        )
        returned_invoices.filtered(lambda x: not x.returned_payment).write(
            {"returned_payment": True}
        )
        (self - returned_invoices).filtered("returned_payment").write(
            {"returned_payment": False}
        )

    @api.depends('type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):    
        self.ensure_one()
        super(AccountInvoice, self)._compute_payments_widget_reconciled_info()
        if not self.returned_payment:
            return True
        if self.invoice_payments_widget != "false":
            info = json.loads(self.invoice_payments_widget)
        else:
            info = {"title": _("Less Payment"), "outstanding": False, "content": []}
        new_content = info["content"]
        returned_reconciles = self.env["account.partial.reconcile"].search(
            [("origin_returned_move_ids.move_id", "=", self.id)]
        )
        for returned_reconcile in returned_reconciles:
            payment = returned_reconcile.credit_move_id
            payment_ret = returned_reconcile.debit_move_id
            new_content.append(
                {
                    "name": payment.name,
                    "journal_name": payment.journal_id.name,
                    "amount": returned_reconcile.amount,
                    "currency": self.currency_id.symbol,
                    "digits": [69, self.currency_id.decimal_places],
                    "position": self.currency_id.position,
                    "date": fields.Date.to_string(payment.date),
                    "payment_id": payment.id,
                    "move_id": payment.move_id.id,
                    "ref": payment.move_id.name,
                }
            )
            new_content.append(
                {
                    "name": payment_ret.name,
                    "journal_name": payment_ret.journal_id.name,
                    "amount": -returned_reconcile.amount,
                    "currency": self.currency_id.symbol,
                    "digits": [69, self.currency_id.decimal_places],
                    "position": self.currency_id.position,
                    "date": fields.Date.to_string(payment_ret.date),
                    "payment_id": payment_ret.id,
                    "move_id": payment_ret.move_id.id,
                    "ref": payment_ret.move_id.name,
                    "returned": True,
                }
            )

        info["content"] = sorted(new_content, key=itemgetter("date"), reverse=True)
        self.invoice_payments_widget = json.dumps(info)

