# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Inventory(models.Model):
    _inherit = "stock.inventory"

    def action_open_inventory_lines(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('stock.stock_inventory_line_tree2').id, 'tree')],
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
#         if not self.inventory_id:
#             context = {
#                 'default_is_editable': False,
#                 'default_inventory_id': self.id,
#                 'default_company_id': self.company_id.id,
#                 'opening_stock':self.opening_stock,
#             }
#         else:
#             context = {
#                 'default_is_editable': True,
#                 'default_inventory_id': self.id,
#                 'default_company_id': self.company_id.id,
#                 'opening_stock':self.opening_stock,
#             }
        context = {
                'default_is_editable': True,
                'default_inventory_id': self.id,
                'default_company_id': self.company_id.id,
                'opening_stock':self.opening_stock,
            }
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids:
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id

        action['context'] = context
        action['domain'] = domain
        return action
    
    def check_picking(self):
        messenger = ''
        picking_id =[] 
        if not self.warehouse_id:
            return
        if not self.product_ids:
            sql = """
                SELECT DISTINCT sp.id picking_id,sp.name picking_name, sp.scheduled_date date,
                to_char(timezone('UTC',sp.scheduled_date::timestamp), 'DD-MM-YYYY HH:MI:SS') scheduled_date
                FROM stock_picking sp
                    JOIN stock_move stm ON stm.picking_id = sp.id
                WHERE sp.warehouse_id = %(warehouse_id)s
                    AND stm.state NOT IN ('done','cancel')
                ORDER BY date
            """%({"warehouse_id": self.warehouse_id.id})
            print(sql)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                messenger += ' - %s: Scheduled Date %s.\n'%(line['picking_name'],line['scheduled_date'])
                picking_id.append(line['picking_id'])
        else:
            join = ""
            where = where_inv = ""
            if self.state == "draft":
                where_inv = " AND inv.id = %s"%(self.id)
            elif self.state == "confirm":
                join = "JOIN stock_inventory_line invl ON (invl.inventory_id = inv.id AND stm.product_id = invl.product_id)"
                where_inv = " AND inv.parent_id = %s"%(self.id)
            if self.product_ids:
                where += ' AND stml.product_id IN (%s)'%(','.join(map(str, [x.id for x in self.product_ids])))
                
            sql = """
                    SELECT DISTINCT pp.id product_id, pp.display_name
                    FROM stock_picking sp
                        JOIN stock_move stm ON stm.picking_id = sp.id
                        JOIN stock_move_line stml on stml.picking_id = sp.id
                        JOIN product_product pp ON pp.id = stm.product_id 
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        JOIN stock_inventory inv ON inv.warehouse_id = sp.warehouse_id
                        %(join)s
                    WHERE stm.state NOT IN ('done','cancel')
                        %(where_inv)s
                        %(where)s    
                """%({"warehouse_id": self.warehouse_id.id, "inv_id": self.id,"where": where, "where_inv": where_inv, "join": join})
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                where2 = ' AND stm.product_id = %s'%(line['product_id'])
                mess = ""
                sql = """
                    SELECT DISTINCT sp.name picking_name,sp.id picking_id
                    FROM stock_picking sp
                        JOIN stock_move stm ON stm.picking_id = sp.id
                    WHERE sp.warehouse_id = %(warehouse_id)s
                        AND stm.state NOT IN ('done','cancel')
                        %(where)s    
                """%({"warehouse_id": self.warehouse_id.id, "where": where2})
                self.env.cr.execute(sql)
                for pick in self.env.cr.dictfetchall():
                    mess += mess and ', %s'%(pick['picking_name']) or '%s'%(pick['picking_name'])
                    picking_id.append(pick['picking_id'])
                messenger += ' - %s: %s.\n'%(line['display_name'], mess)
        res_id = False
        if messenger:
            res_id = self.env['wizard.inventory.mess'].create({'inventory_id': self.id, 'messenger': messenger,'picking_ids':[(6, 0, picking_id)]})
        return res_id
    
    def _get_inventory_lines_values(self):
        vals = []
        Product = self.env['product.product']
        quant_products = self.env['product.product']
        locations = self.env['stock.location'].search([('id', 'child_of', self.location_ids.ids)])
        if not locations:
            locations = self.location_ids
        product_ids = [0]
        if self.product_ids:    
            product_ids = self.product_ids.ids
        product_ids = ','.join(map(str, product_ids))
        sql = '''
            SELECT foo.product_id, foo.location_id, sum(foo.product_qty) product_qty FROM
                (SELECT sml.product_id, 
                    sum(-1*coalesce(sml.product_qty_done,0)) as product_qty,
                    sml.location_id
                FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                WHERE  sm.state = 'done' AND timezone('UTC',sm.date::timestamp) <= timezone('UTC','%(date)s'::timestamp)
                     AND sml.location_id in (%(location_ids)s)  AND sml.product_id in (%(product_ids)s)
                GROUP BY sml.product_id, sml.location_id
                 
                UNION ALL
    
                SELECT sml.product_id, 
                    sum(coalesce(sml.product_qty_done,0)) as product_qty,
                    sml.location_dest_id
                FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
            
                WHERE  sm.state = 'done' AND timezone('UTC',sm.date::timestamp) <= timezone('UTC','%(date)s'::timestamp)
                     AND sml.location_dest_id in (%(location_ids)s)  AND sml.product_id in (%(product_ids)s)
                GROUP BY sml.product_id, sml.location_dest_id) foo
            GROUP BY foo.product_id, foo.location_id
            '''%({'date':self.date,
                 'location_ids':','.join(map(str, [i.id for i in locations])),
                 'product_ids':product_ids})

        self.env.cr.execute(sql)
        for product_data in self.env.cr.dictfetchall():
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if product_data['product_id']:
                product = Product.browse(product_data['product_id']) 
                conversions = product and product.conversion_ids.filtered(lambda x: x.primary)
                product_data['product_uom_id'] = conversions[:1] and conversions[:1].uom_id.id or product.uom_id.id
                product_data['created_by_parent'] = True
                quant_products |= product
            vals.append(product_data)
        return vals
    
    # def action_validate(self):
        # super(Inventory, self).action_validate()
        # self.env['stock.quant']._merge_quants()
        # return True

class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    is_editable = fields.Boolean(help="Technical field to restrict the edition.", default=True)

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    def _onchange_quantity_context(self):
        self = self.with_context(date=self.inventory_id.date)
        super(InventoryLine, self)._onchange_quantity_context()

    @api.model_create_multi
    def create(self, vals_list):
        context = self._context
        if context.get('default_inventory_id', False):
            ctx_inventory_id = context['default_inventory_id']
            inventory_id = self.env['stock.inventory'].browse(ctx_inventory_id)
            self = self.with_context(date=inventory_id.date)
        return super(InventoryLine, self).create(vals_list)
    
    
    
    
    
    
    
    
    
    
    
