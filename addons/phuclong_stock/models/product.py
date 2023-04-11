# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.constrains('active')
    def _check_active(self):
        if not self.active:
            query = """
                SELECT quant.product_id,
                    quant.warehouse_id,
                    quant.wh_lot_id,
                    quant.location_id,
                    SUM(quant.quantity) AS quantity,
                    SUM(quant.reserved_quantity) AS reserved_quantity,
                    SUM(quant.incoming_qty) AS incoming_qty
                FROM (
                    SELECT sq.product_id,
                        sq.warehouse_id,
                        sq.wh_lot_id,
                        sq.location_id,
                        sq.quantity,
                        sq.reserved_quantity,
                        0 AS incoming_qty
                    FROM stock_quant sq
                    WHERE sq.product_id = %(product_id)s

                    UNION ALL

                    SELECT sm.product_id,
                        sm.warehouse_id,
                        sm.location_dest_id AS wh_lot_id,
                        sm.location_dest_id AS location_id,
                        0 AS quantity,
                        0 AS reserved_quantity,
                        sm.product_qty AS incoming_qty
                    FROM stock_move sm
                        JOIN stock_picking_type spt
                            ON spt.id = sm.picking_type_id
                    WHERE sm.state IN (
                            'waiting', 'confirmed',
                            'partially_available', 'assigned')
                        AND sm.product_id = %(product_id)s
                        AND (spt.code = 'incoming'
                                OR
                            (spt.code = 'internal'
                                    AND
                                spt.operation IN ('transit_in', 'move')))
                    ) quant
                GROUP BY quant.product_id,
                    quant.warehouse_id,
                    quant.location_id,
                    quant.wh_lot_id
                HAVING SUM(quant.quantity) != 0
                    OR SUM(quant.reserved_quantity) != 0
                    OR SUM(quant.incoming_qty) != 0
            """ % ({'product_id': self.id})
            self._cr.execute(query)
            res = self._cr.dictfetchall()
            if res:
                raise UserError(_(
                    "The product quantity / "
                    "Incoming quantity / "
                    "Reserved quantity is not 0, "
                    "please adjust the product quantity to 0 "
                    "or cancel the related picking "
                    "before archived the product"))

    @api.constrains('type')
    def _check_product_type(self):
        if self.type == 'service':
            query = '''
                SELECT product_id
                FROM stock_move_line
                WHERE product_id = %(product_id)s

                UNION ALL

                SELECT product_id
                FROM stock_move
                WHERE product_id = %(product_id)s
            ''' % ({'product_id': self.id})
            self._cr.execute(query)
            res = self._cr.dictfetchall()
            if res:
                raise UserError(_(
                    "This product has a warehouse transaction, "
                    "you can not change the product type."))

    @api.model
    def get_theoretical_quantity(
            self, product_id, location_id,
            lot_id=None, package_id=None,
            owner_id=None, to_uom=None):
        date = self._context.get('date') or fields.Datetime.now().date()
        locations = [location_id]
        product_ids = [product_id]
        sql = '''
            SELECT foo.product_id, foo.location_id, sum(foo.product_qty) theoretical_qty FROM
                (SELECT sml.product_id, 
                    sum(-1*coalesce(sml.product_qty_done,0)) as product_qty,
                    sml.location_id
                FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                WHERE  sm.state = 'done' AND timezone('UTC',sm.date::timestamp) <= timezone('UTC','%(date)s'::timestamp)
                     AND sml.location_id = %(location_id)s  AND sml.product_id = %(product_id)s
                GROUP BY sml.product_id, sml.location_id
                 
                UNION ALL
    
                SELECT sml.product_id, 
                    sum(coalesce(sml.product_qty_done,0)) as product_qty,
                    sml.location_dest_id
                FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
            
                WHERE  sm.state = 'done' AND timezone('UTC',sm.date::timestamp) <= timezone('UTC','%(date)s'::timestamp)
                     AND sml.location_dest_id = %(location_id)s  AND sml.product_id = %(product_id)s
                GROUP BY sml.product_id, sml.location_dest_id) foo
            GROUP BY foo.product_id, foo.location_id
            '''%({'date':date,
                 'location_id':location_id,
                 'product_id':product_id})
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        theoretical_qty = result and result[0]['theoretical_qty'] or 0
        return theoretical_qty


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains('active')
    def _check_active(self):
        if not self.active:
            query = """
                SELECT quant.product_id,
                    quant.warehouse_id,
                    quant.wh_lot_id,
                    quant.location_id,
                    SUM(quant.quantity) AS quantity,
                    SUM(quant.reserved_quantity) AS reserved_quantity,
                    SUM(quant.incoming_qty) AS incoming_qty
                FROM (
                    SELECT sq.product_id,
                        sq.warehouse_id,
                        sq.wh_lot_id,
                        sq.location_id,
                        sq.quantity,
                        sq.reserved_quantity,
                        0 AS incoming_qty
                    FROM stock_quant sq
                        JOIN product_product pp ON pp.id = sq.product_id
                    WHERE pp.product_tmpl_id = %(product_tmpl_id)s

                    UNION ALL

                    SELECT sm.product_id,
                        sm.warehouse_id,
                        sm.location_dest_id AS wh_lot_id,
                        sm.location_dest_id AS location_id,
                        0 AS quantity,
                        0 AS reserved_quantity,
                        sm.product_qty AS incoming_qty
                    FROM stock_move sm
                        JOIN stock_picking_type spt
                            ON spt.id = sm.picking_type_id
                        JOIN product_product pp ON pp.id = sm.product_id
                    WHERE sm.state IN (
                            'waiting', 'confirmed',
                            'partially_available', 'assigned')
                        AND pp.product_tmpl_id = %(product_tmpl_id)s
                        AND (spt.code = 'incoming'
                                OR
                            (spt.code = 'internal'
                                    AND
                                spt.operation IN ('transit_in', 'move')))
                    ) quant
                GROUP BY quant.product_id,
                    quant.warehouse_id,
                    quant.location_id,
                    quant.wh_lot_id
                HAVING SUM(quant.quantity) != 0
                    OR SUM(quant.reserved_quantity) != 0
                    OR SUM(quant.incoming_qty) != 0
            """ % ({'product_tmpl_id': self.id})
            self._cr.execute(query)
            res = self._cr.dictfetchall()
            if res:
                raise UserError(_(
                    "The product quantity / "
                    "Incoming quantity / "
                    "Reserved quantity is not 0, "
                    "please adjust the product quantity to 0 "
                    "or cancel the related picking "
                    "before archived the product"))

    @api.constrains('type')
    def _check_product_type(self):
        if self.type == 'service':
            query = '''
                SELECT sml.product_id
                FROM stock_move_line sml
                    JOIN product_product pp ON pp.id = sml.product_id
                WHERE pp.product_tmpl_id = %(product_tmpl_id)s

                UNION ALL

                SELECT sm.product_id
                FROM stock_move sm
                    JOIN product_product pp ON pp.id = sm.product_id
                WHERE pp.product_tmpl_id = %(product_tmpl_id)s
            ''' % ({'product_tmpl_id': self.id})
            self._cr.execute(query)
            res = self._cr.dictfetchall()
            if res:
                raise UserError(_(
                    "This product has a warehouse transaction, "
                    "you can not change the product type."))
