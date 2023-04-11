# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.tools.float_utils import float_round
import datetime


class ProductProduct(models.Model):
    _inherit = "product.product"

    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_ref_code', True) and d.get('ref_code', False) or False
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(['name', 'ref_code', 'product_tmpl_id'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids

        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('name', 'in', partner_ids),
            ])
            # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
            # Use `load=False` to not call `name_get` for the `product_tmpl_id` and `product_id`
            supplier_info.sudo().read(['product_tmpl_id', 'product_id', 'product_name', 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'ref_code': s.product_code or product.ref_code,
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'ref_code': product.ref_code,
                          }
                result.append(_name_get(mydict))
        return result

    @api.depends('name','product_tmpl_id.name', 'product_tmpl_id.ref_code', 'product_template_attribute_value_ids.name', 'product_template_attribute_value_ids.attribute_id')
    def _get_display_name(self):
        for pp in self:
            if pp.ref_code:
                pp.display_name = '[%s] %s' % (pp.ref_code, pp.name)
            else:
                pp.display_name = pp.name
                
    display_name = fields.Char(compute='_get_display_name', string="Display Name", store=True, index=True, translate=True)

    pos_sequence = fields.Integer(related="product_tmpl_id.pos_sequence", string="Pos Sequence", default=0, readonly=True)

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if self._context.get('buy_phuclong', False):
            if self._context.get('product_average', False):
                date_date_expected_domain_to = [
                    ('date_expected', '<=', to_date),
                    ]
            else:
                date_date_expected_domain_to = [('date', '<=', to_date),
                                                ('date', '>=', from_date),]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to
        else:
            if from_date:
                date_date_expected_domain_from = [
                    '|',
                        '&',
                            ('state', '=', 'done'),
                            ('date', '<=', from_date),
                        '&',
                            ('state', '!=', 'done'),
                            ('date_expected', '<=', from_date),
                ]
                domain_move_in += date_date_expected_domain_from
                domain_move_out += date_date_expected_domain_from
            if to_date:
                date_date_expected_domain_to = [
                    '|',
                        '&',
                            ('state', '=', 'done'),
                            ('date', '<=', to_date),
                        '&',
                            ('state', '!=', 'done'),
                            ('date_expected', '<=', to_date),
                ]
                date_date_expected_domain_to = [('date', '<=', to_date), ]
                domain_move_in += date_date_expected_domain_to
                domain_move_out += date_date_expected_domain_to
        
        Move = self.env['stock.move']
        Quant = self.env['stock.quant']
        
        if self._context.get('buy_phuclong', False):
            if self._context.get('picking_type_id', False):
                domain_move_out += [('picking_type_id', '=', self._context.get('picking_type_id', False))]
            if self._context.get('product_average', False):
                domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
                domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
                moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
                moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            else:
                domain_move_in_todo = [('state', '=', 'done')] + domain_move_in
                domain_move_out_todo = [('state', '=', 'done')] + domain_move_out
                moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
                moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        else:
            domain_move_in_todo = [('state', '=', ('done'))] + domain_move_in
            domain_move_out_todo = [('state', '=', 'done')] + domain_move_out
            moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))

        
        quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'], ['product_id'], orderby='id'))
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            if self._context.get('product_average', False) or self._context.get('buy_phuclong', False):
                # Điều kiện domain dự kiến
                domain_move_in_done = [('state', 'in', ['waiting', 'confirmed', 'assigned', 'partially_available']), ('date', '>', to_date)] + domain_move_in_done
                domain_move_out_done = [('state', 'in', ['waiting', 'confirmed', 'assigned', 'partially_available']), ('date', '>', to_date)] + domain_move_out_done
            else:
                domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
                domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            if not product_id:
                res[product_id] = dict.fromkeys(
                    ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available'],
                    0.0,
                )
                continue
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(product_id, [0.0])[0] - moves_in_res_past.get(product_id, 0.0) + moves_out_res_past.get(product_id, 0.0)
            else:
                qty_available = quants_res.get(product_id, [0.0])[0]
            reserved_quantity = quants_res.get(product_id, [False, 0.0])[1]
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)

        return res
    
    #Vuong: disable select seller to update price purchase
    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        self.ensure_one()
        Supplierinfo = self.env['product.supplierinfo']
        ctx = self._context.copy()
        if ctx.get('buy_phuclong', False):
            # Tuan: xử lý vấn đề search supplier cho quy tác tái cung ứng
            supplier = self.env['res.partner'].search([
                ('supplier', '=', True),
                ('is_default_vendor', '=', True),
                ], limit=1)
            supplierinfo_id = Supplierinfo.search(
                [('name', '=', supplier.id)], limit=1)
            if not supplierinfo_id:
                supplierinfo_id = Supplierinfo.create({
                    'name': supplier.id,
                    'min_qty': 1,
                    'price': 0.0,
                    'delay': 0,
                })
            return supplierinfo_id
        return Supplierinfo
