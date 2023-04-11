# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class StockCurrentInventory(models.Model):
    _name = "stock.current.inventory"
    _rec_name = "product_id"
    _auto = False

    product_id = fields.Many2one('product.product', string="Product")
    product_uom_id = fields.Many2one('uom.uom', string="UoM")
    default_code = fields.Char(string='SKU')
    barcode = fields.Char(string='Barcode')
    ref_code = fields.Char('Reference Code')
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    wh_lot_id = fields.Many2one("stock.location", string='Source location')
    location_id = fields.Many2one('stock.location', string="Storage Location")
    quantity = fields.Float(
        string="Quantity",
        digits=(16, 3))
    reserved_quantity = fields.Float(
        string="Reserved Quantity",
        digits=(16, 3))
    incoming_qty = fields.Float(
        string="Incoming Quantity",
        digits=(16, 3))
    virtual_available = fields.Float(
        string="Available Quantity",
        digits=(16, 3))
    company_account_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Company Account Analytic')
    company_id = fields.Many2one('res.company', string='Company')
    
    # @api.model
    # def load_views(self, views, options=None):
        # self.env['stock.quant']._merge_quants()
        # self._cr.execute('''
            # UPDATE stock_quant quant
            # SET quantity = foo1.product_qty,
            # reserved_quantity = foo1.reserved_qty,
            # virtual_available = foo1.product_qty - foo1.reserved_qty
            # FROM (
                # SELECT foo.product_id, foo.location_id, sum(foo.product_qty) product_qty, sum(foo.reserved_qty) reserved_qty FROM
                            # (SELECT sml.product_id, 
                            # SUM(CASE WHEN sml.state = 'done' THEN -1*COALESCE(sml.product_qty_done,0)
                    # ELSE 0 END) as product_qty,
                            # SUM(CASE WHEN sml.state = 'assigned' THEN COALESCE(sml.product_qty, 0)
                    # ELSE 0 END) AS reserved_qty,
                            # sml.location_id
                            # FROM stock_move_line sml
                                # JOIN stock_move sm ON sm.id = sml.move_id
                            # WHERE  sm.state in ('assigned', 'done')
                            # GROUP BY sml.product_id, sml.location_id
                            #
                            # UNION ALL
                            #
                            # SELECT sml.product_id, 
                                # sum(coalesce(sml.product_qty_done,0)) as product_qty,
                                # 0 reserved_qty,
                                # sml.location_dest_id
                            # FROM stock_move_line sml
                                # JOIN stock_move sm ON sm.id = sml.move_id
                                #
                            # WHERE  sm.state = 'done'
                            # GROUP BY sml.product_id, sml.location_dest_id) foo
                        # GROUP BY foo.product_id, foo.location_id
                  # ) foo1
            # WHERE quant.product_id = foo1.product_id and quant.location_id = foo1.location_id and 
            # (quant.quantity != foo1.product_qty or quant.reserved_quantity != foo1.reserved_qty);
        # ''')
        # return super(StockCurrentInventory, self).load_views(views, options=options)

    def init(self):
        self.env['stock.quant']._merge_quants()
        cr = self._cr
        tools.drop_view_if_exists(cr, self._table)
        query = """
            CREATE OR REPLACE VIEW stock_current_inventory AS (
                SELECT row_number() OVER () AS id,
                    quant.product_id,
                    pt.uom_id AS product_uom_id,
                    pt.default_code,
                    pp.barcode,
                    pt.ref_code,
                    quant.warehouse_id,
                    quant.wh_lot_id,
                    quant.location_id,
                    SUM(quant.quantity) AS quantity,
                    SUM(quant.reserved_quantity) AS reserved_quantity,
                    SUM(quant.incoming_qty) AS incoming_qty,
                    SUM(quant.virtual_available) AS virtual_available,
                    quant.company_account_analytic_id,
                    quant.company_id
                FROM product_product pp
                    JOIN (
                        SELECT sq.product_id,
                            sq.warehouse_id,
                            sq.wh_lot_id,
                            sq.location_id,
                            sq.quantity,
                            sq.reserved_quantity,
                            0 AS incoming_qty,
                            sq.virtual_available AS virtual_available,
                            sq.company_account_analytic_id,
                            sq.company_id
                        FROM stock_quant sq

                        UNION ALL

                        SELECT sm.product_id,
                            sm.warehouse_id,
                            sm.location_dest_id AS wh_lot_id,
                            sm.location_dest_id AS location_id,
                            0 AS quantity,
                            0 AS reserved_quantity,
                            sm.product_qty AS incoming_qty,
                            sm.product_qty AS virtual_available,
                            sm.company_account_analytic_id,
                            sm.company_id
                        FROM stock_move sm
                            JOIN stock_picking_type spt
                                ON spt.id = sm.picking_type_id
                        WHERE sm.state IN (
                                'waiting', 'confirmed',
                                'partially_available', 'assigned')
                            AND (spt.code = 'incoming'
                                    OR
                                (spt.code = 'internal'
                                        AND
                                    spt.operation IN ('transit_in', 'move')))
                    ) quant ON quant.product_id = pp.id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                GROUP BY quant.product_id,
                    pt.uom_id,
                    pt.default_code,
                    pp.barcode,
                    pt.ref_code,
                    quant.warehouse_id,
                    quant.location_id,
                    quant.company_account_analytic_id,
                    quant.company_id,
                    quant.wh_lot_id
            )
        """
        cr.execute(query)
