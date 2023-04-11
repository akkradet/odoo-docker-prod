# -*- coding: utf-8 -*-
from psycopg2 import OperationalError, Error

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    ref_code = fields.Char(related='product_id.ref_code',
                           string='Reference Code', readonly=True, store=True)
    
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, digits='Product Unit of Measure')
    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0, digits='Product Unit of Measure',
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=True, required=True)
    virtual_available = fields.Float(string='Available Quantity', help="Available Quantity = Quantity - Reserved Quantity", digits='Product Unit of Measure')


    @api.model
    def update_stock_qty(self):
        self._merge_quants()

    @api.model
    def _merge_quants(self):
        query = """
            WITH
                dupes AS (
                    SELECT min(id) as to_update_quant_id,
                        (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                        SUM(reserved_quantity) as reserved_quantity,
                        SUM(quantity) as quantity
                    FROM stock_quant
                    GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id, warehouse_id, in_date
                    HAVING count(id) > 1
                ),
                _up_q AS (
                    UPDATE stock_quant q
                        SET quantity = d.quantity,
                            reserved_quantity = d.reserved_quantity,
                            virtual_available = d.quantity - d.reserved_quantity
                    FROM dupes d
                    WHERE d.to_update_quant_id = q.id
                )
            DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes);
            
            UPDATE stock_quant quant
            SET quantity = foo1.product_qty,
            reserved_quantity = foo1.reserved_qty,
            virtual_available = foo1.product_qty - foo1.reserved_qty
            FROM (
                SELECT foo.product_id, foo.location_id, sum(foo.product_qty) product_qty, sum(foo.reserved_qty) reserved_qty FROM
                            (SELECT sml.product_id, 
                            SUM(CASE WHEN sml.state = 'done' THEN -1*COALESCE(sml.product_qty_done,0)
                    ELSE 0 END) as product_qty,
                            SUM(CASE WHEN sml.state = 'assigned' THEN COALESCE(sml.product_qty, 0)
                    ELSE 0 END) AS reserved_qty,
                            sml.location_id
                            FROM stock_move_line sml
                                JOIN stock_move sm ON sm.id = sml.move_id
                            WHERE  sm.state in ('assigned', 'done')
                            GROUP BY sml.product_id, sml.location_id
                             
                            UNION ALL
                
                            SELECT sml.product_id, 
                                sum(coalesce(sml.product_qty_done,0)) as product_qty,
                                0 reserved_qty,
                                sml.location_dest_id
                            FROM stock_move_line sml
                                JOIN stock_move sm ON sm.id = sml.move_id
                        
                            WHERE  sm.state = 'done'
                            GROUP BY sml.product_id, sml.location_dest_id) foo
                        GROUP BY foo.product_id, foo.location_id
                  ) foo1
            WHERE quant.product_id = foo1.product_id and quant.location_id = foo1.location_id and 
            (quant.quantity != foo1.product_qty or quant.reserved_quantity != foo1.reserved_qty);
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(query)
        except Error as e:
            _logger.info('an error occured while merging quants: %s', e.pgerror)
