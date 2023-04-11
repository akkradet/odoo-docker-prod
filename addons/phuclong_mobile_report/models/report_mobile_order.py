# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class MobileOrderReport(models.Model):
    _name = 'report.mobile.order'
    _description = "Mobile Orders Report"
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Order Date', readonly=True)
    order_id = fields.Many2one('pos.order', string='Order', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', readonly=True)
    state = fields.Selection(
        [('draft', 'New'), ('paid', 'Paid'), ('done', 'Posted'),
         ('invoiced', 'Invoiced'), ('cancel', 'Cancelled')],
        string='Status')
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    price_total = fields.Float(string='Total Price', readonly=True)
    price_sub_total = fields.Float(
        string='Subtotal w/o discount', readonly=True)
    total_discount = fields.Float(string='Total Discount', readonly=True)
    average_price = fields.Float(
        string='Average Price', readonly=True, group_operator="avg")
    location_id = fields.Many2one(
        'stock.location', string='Location', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)
    nbr_lines = fields.Integer(string='Sale Line Count', readonly=True)
    product_qty = fields.Integer(string='Product Quantity', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    delay_validation = fields.Integer(string='Delay Validation')
    product_categ_id = fields.Many2one(
        'product.category', string='Product Category', readonly=True)
    invoiced = fields.Boolean(readonly=True)
    config_id = fields.Many2one(
        'pos.config', string='Point of Sale', readonly=True)
    mobile_category_id = fields.Many2one(
        'product.category.mobile', string='PoS Category Mobile', readonly=True)
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', readonly=True)
    session_id = fields.Many2one(
        'pos.session', string='Session', readonly=True)

    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location', readonly=True)
    cashier_id = fields.Many2one(
        'hr.employee', string='Cashier', readonly=True)
    saleman_id = fields.Many2one(
        'hr.employee', string='Salesman', readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', readonly=True)
    loyalty_discount_amount = fields.Float(
        string='Loyalty Discount Amount', readonly=True)
    sale_type_id = fields.Many2one(
        'pos.sale.type', string='Sale Type', readonly=True)
    order_status_app = fields.Selection([('new', 'New'),
                                          ('done', 'Done'),
                                          ('cancel', 'Cancel')], string="Status Mobile")

    def _select(self):
        return """
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS nbr_lines,
                s.date_order AS date,
                SUM(l.qty) AS product_qty,
                SUM(l.qty * l.price_unit) AS price_sub_total,
                (SUM((l.qty * l.price_unit) * ((100 - l.discount) / 100) *((100 - l.loyalty_discount_percent) / 100)) - (case when (l.price_subtotal_incl > 0 and s.discount_amount!= 0) then
            (l.price_subtotal_incl)/(select sum(price_subtotal_incl) from pos_order_line where order_id = s.id and price_subtotal_incl>0)*(-s.discount_amount)
            else 0 end) - l.discount_amount) AS price_total,
                (SUM((l.qty * l.price_unit) * (l.discount / 100)) + (case when (l.price_subtotal_incl > 0 and s.discount_amount!= 0) then
            (l.price_subtotal_incl)/(select sum(price_subtotal_incl) from pos_order_line where order_id = s.id and price_subtotal_incl>0)*(-s.discount_amount)
            else 0 end) + l.discount_amount) AS total_discount,
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
                pt.mobile_category_id,
                s.location_id stock_location_id,
                s.pricelist_id,
                s.session_id,
                s.invoice_id IS NOT NULL AS invoiced,
                s.warehouse_id,
                s.cashier_id,
                l.saleman_id,
                s.sale_type_id,
                s.order_status_app
        """

    def _from(self):
        return """
            FROM pos_order_line AS l
                INNER JOIN pos_order s ON (s.id=l.order_id)
                LEFT JOIN product_product p ON (l.product_id=p.id)
                LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
                LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                LEFT JOIN pos_sale_type pst ON (s.sale_type_id=pst.id)
        """

    def _where(self):
        return """
            WHERE
                s.order_in_app IS TRUE
                AND pst.use_for_app IS TRUE
        """

    def _group_by(self):
        return """
            GROUP BY
                s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                s.user_id, s.location_id, s.company_id, s.sale_journal,
                s.pricelist_id, s.invoice_id, s.create_date, s.session_id,s.warehouse_id,
                s.cashier_id,
                l.saleman_id,
                l.product_id,
                pt.categ_id, pt.mobile_category_id,
                p.product_tmpl_id,
                ps.config_id,
                s.location_id,
                l.price_subtotal_incl,
                l.discount_amount,
                s.sale_type_id,
                s.order_status_app
        """

    def _having(self):
        return """
            HAVING
                SUM(l.qty * u.factor) != 0
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by(), self._having())
        )
