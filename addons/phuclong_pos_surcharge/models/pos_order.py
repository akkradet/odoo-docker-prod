# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    total_surcharge = fields.Float('Surcharge')

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['total_surcharge'] = ui_order.get('total_surcharge', False)
        return fields


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    amount_surcharge = fields.Float('Surcharge Amount')


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"

    amount_surcharge = fields.Float(string='Surcharge', readonly=True)

    def _group_by(self):
        return """
            GROUP BY
                s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                s.user_id, s.location_id, s.company_id, s.sale_journal,
                s.pricelist_id, s.invoice_id, s.create_date, s.session_id,s.warehouse_id,
                s.cashier_id,
                l.saleman_id,
                l.id,
                l.product_id,
                pt.categ_id, pt.pos_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                s.location_id,
                l.price_subtotal_incl,
                l.amount_surcharge,
                l.discount_amount
        """

    def _select(self):
        # Thái: + amount_surcharge trên orderline vào price_total của Báo cáo bán hàng
        return """
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS nbr_lines,
                s.date_order AS date,
                SUM(l.qty) AS product_qty,
                SUM(l.price_unit*l.qty) AS price_sub_total,
                (SUM(l.price_subtotal_incl + (case when (l.amount_surcharge != 0) 
                then (l.amount_surcharge) else 0 end) - case when (l.price_subtotal_incl > 0 and s.discount_amount!= 0) then
            (l.price_subtotal_incl)/(s.amount_total - s.discount_amount)*(-s.discount_amount)
            else 0 end)) AS price_total,
            (SUM(l.amount_surcharge)) as amount_surcharge,
                ROUND(ABS(SUM((l.price_unit*qty-l.price_subtotal_incl) + (case when (l.price_subtotal_incl > 0 and s.discount_amount!= 0) then
            (l.price_subtotal_incl)/(s.amount_total - s.discount_amount)*(-s.discount_amount)
            else 0 end)))::numeric, 5) AS total_discount,
                (SUM(l.qty*l.price_unit)/SUM(l.qty * u.factor))::decimal AS average_price,
                SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                SUM((l.qty * l.price_unit) * ((100 - l.discount) / 100) * (l.loyalty_discount_percent / 100)) AS loyalty_discount_amount,
                s.id as order_id,
                s.partner_id AS partner_id,
                s.state AS state,
                s.user_id AS user_id,
                s.location_id AS location_id,
                s.company_id AS company_id,
                s.sale_journal AS journal_id,
                l.product_id AS product_id,
                pt.categ_id AS product_categ_id,
                p.product_tmpl_id,
                ps.config_id,
                pt.pos_categ_id,
                s.location_id stock_location_id,
                s.pricelist_id,
                s.session_id,
                s.invoice_id IS NOT NULL AS invoiced,
                s.warehouse_id,
                s.cashier_id,
                l.saleman_id
        """