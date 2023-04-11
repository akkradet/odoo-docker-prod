# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Inventory(models.Model):
    _inherit = "stock.inventory"

    def action_template(self):
        return self.env.ref('phuclong_stock.report_stock_inventory_template').report_action(self)

    def get_product_by_warehouse(self, warehouse_id, location_ids):
        res = list()
        proudct_ids = ''
        for locationin in location_ids:
            res += self.get_product_by_warehouse_location(warehouse_id, locationin.id, proudct_ids)
            proudct_ids += ', '.join(map(str, [x['id'] for x in res]))
        return res

    def get_product_by_warehouse_location(self, warehouse_id, location_id, proudct_ids):
        if proudct_ids:
            proudct_ids = 'AND pp.id NOT IN (%s)' % proudct_ids
        sql = '''
        select pp.id,pp.default_code, pt.name as product_name, pt.ref_code, uom.name as uom_name
        from
            (select
                CASE
                    WHEN SUM(sq.virtual_available) = 0 THEN sq.product_id
                END  product_id
             --,sq.product_id, SUM(sq.virtual_available)
            from stock_quant sq
            where sq.product_id in (select distinct(sm.product_id)
                                    from stock_move sm
                                    where timezone('UTC',sm.date::timestamp) > (select to_char(max(inv.date),'YYYY-mm-dd HH:MI:SS')::timestamp
                                                                                 --,timezone('UTC',max(inv.date)::timestamp)
                                                                                from stock_inventory inv
                                                                                left join stock_inventory_stock_location_rel rel_location 
                                                                                    on inv.id = rel_location.stock_inventory_id
                                                                                where inv.state = 'done'
                                                                                and inv.warehouse_id = %(warehouse_id)s
                                                                                and rel_location.stock_location_id = %(location_id)s)
                                    and sm.warehouse_id = %(warehouse_id)s
                                    and sm.location_id = %(location_id)s
                                    and sm.location_dest_id != %(location_id)s
                                    and sm.state = 'done'
                                    group by sm.product_id)
            and sq.location_id = %(location_id)s
            and sq.warehouse_id = %(warehouse_id)s
            group by sq.product_id) as res
        left join product_product pp on pp.id = res.product_id
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join uom_uom uom on uom.id = pt.uom_id
        where res.product_id is not null
            AND pp.active = TRUE
        %(proudct_ids)s
        UNION
        
        select pp.id, pp.default_code, pt.name as product_name, pt.ref_code, uom.name as uom_name
        from product_product pp
        left join product_template pt on pt.id = pp.product_tmpl_id
        left join uom_uom uom on uom.id = pt.uom_id
        where pp.id in (select
                        CASE 
                            WHEN SUM(sq.virtual_available) != 0 THEN sq.product_id
                        END
                       from stock_quant sq
                       where sq.virtual_available != 0
                       and sq.location_id = %(location_id)s
                       and sq.warehouse_id = %(warehouse_id)s
                       group by sq.product_id)
            AND pp.active = TRUE
        %(proudct_ids)s
        ''' % ({'warehouse_id': warehouse_id,
                'location_id': location_id,
                'proudct_ids': proudct_ids,
                })
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return res
