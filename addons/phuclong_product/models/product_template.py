# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def init(self):
        field_id = self.env['ir.model.fields']._get(
            self._name, 'type').selection_ids.filtered(lambda l: l.value == 'consu')
        if field_id:
            self._cr.execute(
                'DELETE FROM ir_model_fields_selection WHERE id = %s' % (field_id.id))
        return

    name = fields.Char('Name', index=True, required=True,
                       track_visibility='onchange', translate=False)
    pos_sequence = fields.Integer('Pos Sequence', default=0, copy=False)
    short_name = fields.Char('Short Name', copy=False)
    eng_name = fields.Char('English Name')
    size_id = fields.Many2one('product.size', string='Size', copy=False)
    ref_code = fields.Char('Reference Code', copy=False, tracking=True)
    lock_item_method = fields.Selection(
        [('manual', 'Manual'), ('auto', 'Auto')], string='Lock Item Method', default='manual')
    fnb_type = fields.Selection([('topping', 'Topping'), ('food', 'Food'),
                                 ('drink', 'Drink'), ('cup',
                                                      'Cup'), ('lid', 'Lid'),
                                 ('packaged_product', 'Packaged Product'),
                                 ('customizable_material',
                                  'Customizable Material'),
                                 ('material', 'Material')], related='categ_id.fnb_type', string='FnB Type', readonly=True, store=True)
    lid_id = fields.Many2one(
        'product.template', string='Lid', domain="[('categ_id.fnb_type','=','lid')]", tracking=True)
    cup_type = fields.Selection(
        [('paper', 'Paper'), ('plastic', 'Plastic')], string="Cup Type")
    suitable_topping_ids = fields.Many2many(
        'product.template',
        'template_topping_rel',
        'product_tmpl_id',
        'topping_id',
        string='Topping')
    product_material_ids = fields.One2many(
        'product.material', 'product_id',
        string='Product Material', inverse=False)
    custom_material_ids = fields.One2many(
        'product.material', 'product_custom_id', string='Custom Materials', inverse=False)
    is_cashless = fields.Boolean(default=False)
    update_coupon_expiration = fields.Boolean(default=False)
    effective_day = fields.Integer('Effective Day', default=0)

    lst_price = fields.Float(tracking=False)
    list_price = fields.Float(tracking=True)

    @api.constrains('is_cashless', 'effective_day', 'update_coupon_expiration')
    def _check_effective_day(self):
        for product in self:
            if (product.is_cashless or product.update_coupon_expiration) and product.effective_day <= 0:
                raise UserError(_('Effective Day must >= 0'))
            
    @api.onchange('is_cashless')
    def onchange_is_cashless(self):
        if self.is_cashless:
            if self.update_coupon_expiration:
                self.update_coupon_expiration = False
                
    @api.onchange('update_coupon_expiration')
    def onchange_update_coupon_expiration(self):
        if self.update_coupon_expiration:
            if self.is_cashless:
                self.is_cashless = False

    def _get_string_tracking_log(self, object, field):
        field_id = self.env['ir.model.fields'].sudo().search(
            [('model_id', '=', object._name), ('name', '=', field)])
        return field_id and field_id.field_description or str(getattr(object._fields[field], 'string'))

    def _get_tracking_log(self, object=False, field='', old_value=False, new_value=False):
        changed_field = self._get_string_tracking_log(object, field)
        type_field = str(getattr(object._fields[field], 'type'))
        return self.__get_tracking_log(changed_field, type_field, old_value, new_value)

    def __get_tracking_log(self, changed_field=False, type_field=False, old_value=False, new_value=False):
        message = '<li>'
        message += '%s:' % changed_field
        if old_value != False:
            message += '<span> %s </span>' % old_value
            if old_value != new_value:
                message += '<span class="fa fa-long-arrow-right" role="img" aria-label="%(changed)s" title="%(changed)s"></span>' % {
                    'changed': _('Changed')}
        if old_value != new_value or (old_value == False and new_value == 0):
            message += '<span> %s </span>' % new_value
        message += '</li>'
        return message

    def __get_tracking_log_create(self, create_field=False, message_create=''):
        return '<li><span class="fa fa-plus" role="img" aria-label="%(field)s" title="%(field)s"></span> %(field)s%(message)s</li>' % {'field': create_field, 'message': message_create}

    def __get_tracking_log_edit(self, edit_field=False, message_edit=''):
        return '<li><span class="fa fa-pencil" role="img" aria-label="%(field)s" title="%(field)s"></span> %(field)s%(message)s</li>' % {'field': edit_field, 'message': message_edit}

    def __get_tracking_log_unlink(self, unlink_field=False):
        return '<li><span class="fa fa-trash" role="img" aria-label="%(field)s" title="%(field)s"></span> %(field)s</li>' % {'field': unlink_field}

    def __set_log_note_cup(self, values):
        self.ensure_one()
        field = 'cup_ids'
        message = '<ul class="o_mail_thread_message_tracking">'
        message += '<li><strong>'
        message += self._get_string_tracking_log(
            self, field)
        message += '</strong><ul class="style_type_none">'
        for vals in values.get(field):
            if vals[0] == 0:
                val = vals[2]
                message_create = '<ul class="style_type_none">'
                for val_k, val_v in val.items():
                    if val_k == 'cup_line_ids':
                        for data in val_v:
                            if data[0] == 0:
                                cup_line_id = self.env['product.cup.line'].sudo(
                                ).browse()
                                data_val = data[2]
                                cup_id = self.env['product.template'].sudo().browse(
                                    data_val.get('cup_id', False))
                                message_create += '<li>'
                                message_create += cup_id and cup_id.display_name or ''
                                message_create += '<ul class="style_type_none">'
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_create += self._get_tracking_log(
                                            cup_line_id, data_k, False, data_v)
                                message_create += '</ul>'
                                message_create += '</li>'
                message_create += '</ul>'
                sale_type_id = self.env['pos.sale.type'].sudo().browse(
                    val.get('sale_type_id', False))
                message += self.__get_tracking_log_create(
                    sale_type_id and sale_type_id.display_name or '', message_create)
            if vals[0] == 1:
                cup_default_id = getattr(self, field).filtered(
                    lambda cd: cd.id == vals[1])
                message_edit_1 = '<ul class="style_type_none">'
                val = vals[2]
                for val_k, val_v in val.items():
                    if val_k == 'sale_type_id':
                        sale_type_id = self.env['pos.sale.type'].sudo().browse(
                            val_v)
                        message_edit_1 += self._get_tracking_log(
                            cup_default_id, val_k, cup_default_id.sale_type_id and cup_default_id.sale_type_id.display_name or False, sale_type_id.display_name)
                    if val_k == 'cup_line_ids':
                        for data in val_v:
                            if data[0] == 0:
                                cup_line_id = cup_default_id.cup_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                data_val = data[2]
                                cup_id = self.env['product.template'].sudo().browse(
                                    data_val.get('cup_id', False))
                                message_create = '<ul class="style_type_none">'
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_create += self._get_tracking_log(
                                            cup_line_id, data_k, False, data_v)
                                message_create += '</ul>'
                                message_edit_1 += self.__get_tracking_log_create(
                                    cup_id and cup_id.display_name or '', message_create)
                            if data[0] == 1:
                                cup_line_id = cup_default_id.cup_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                message_edit = '<ul class="style_type_none">'
                                data_val = data[2]
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_edit += self._get_tracking_log(
                                            cup_line_id, data_k, cup_line_id.sequence, data_v)
                                    if data_k == 'cup_id':
                                        cup_id = self.env['product.template'].sudo().browse(
                                            data_v)
                                        message_edit += self._get_tracking_log(
                                            cup_line_id, data_k, cup_line_id.cup_id.display_name, cup_id.display_name)
                                message_edit += '</ul>'
                                message_edit_1 += self.__get_tracking_log_edit(
                                    cup_line_id.cup_id and cup_line_id.cup_id.display_name or '', message_edit)
                            if data[0] == 2:
                                cup_line_id = cup_default_id.cup_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                message_edit_1 += self.__get_tracking_log_unlink(
                                    cup_line_id.cup_id and cup_line_id.cup_id.display_name or '')
                message_edit_1 += '</ul>'
                message += self.__get_tracking_log_edit(
                    cup_default_id.sale_type_id and cup_default_id.sale_type_id.display_name or cup_default_id.display_name, message_edit_1)
            if vals[0] == 2:
                cup_default_id = getattr(self, field).filtered(
                    lambda cd: cd.id == vals[1])
                message += self.__get_tracking_log_unlink(
                    cup_default_id.sale_type_id and cup_default_id.sale_type_id.display_name or cup_default_id.display_name)
        message += '</li>'
        message += '</ul>'
        return message

    def __set_log_note_material(self, values, field):
        self.ensure_one()
        message = '<ul class="o_mail_thread_message_tracking">'
        message += '<li><strong>'
        message += self._get_string_tracking_log(
            self, field)
        message += '</strong><ul class="style_type_none">'
        for vals in values.get(field):
            if vals[0] == 0:
                val = vals[2]
                message_create = '<ul class="style_type_none">'
                for val_k, val_v in val.items():
                    if val_k == 'material_line_ids':
                        for data in val_v:
                            if data[0] == 0:
                                material_line_id = self.env['product.material.line'].sudo(
                                ).browse()
                                data_val = data[2]
                                product_id = self.env['product.template'].sudo().browse(
                                    data_val.get('product_id', False))
                                message_create += '<li>'
                                message_create += product_id and product_id.display_name or ''
                                message_create += '<ul class="style_type_none">'
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_create += self._get_tracking_log(
                                            material_line_id, data_k, False, data_v)
                                    if data_k == 'product_qty':
                                        message_create += self._get_tracking_log(
                                            material_line_id, data_k, False, data_v)
                                message_create += '</ul>'
                                message_create += '</li>'
                message_create += '</ul>'
                message += self.__get_tracking_log_create(
                    val.get('name', ''), message_create)
            if vals[0] == 1:
                product_material_id = getattr(self, field).filtered(
                    lambda pm: pm.id == vals[1])
                message_edit_1 = '<ul class="style_type_none">'
                val = vals[2]
                for val_k, val_v in val.items():
                    if val_k == 'name':
                        message_edit_1 += self._get_tracking_log(
                            product_material_id, val_k, product_material_id.name, val_v)
                    if val_k == 'material_line_ids':
                        for data in val_v:
                            if data[0] == 0:
                                material_line_id = product_material_id.material_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                data_val = data[2]
                                product_id = self.env['product.template'].sudo().browse(
                                    data_val.get('product_id', False))
                                message_create = '<ul class="style_type_none">'
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_create += self._get_tracking_log(
                                            material_line_id, data_k, False, data_v)
                                    if data_k == 'product_qty':
                                        message_create += self._get_tracking_log(
                                            material_line_id, data_k, False, data_v)
                                message_create += '</ul>'
                                message_edit_1 += self.__get_tracking_log_create(
                                    product_id and product_id.display_name or '', message_create)
                            if data[0] == 1:
                                material_line_id = product_material_id.material_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                message_edit = '<ul class="style_type_none">'
                                data_val = data[2]
                                for data_k, data_v in data_val.items():
                                    if data_k == 'sequence':
                                        message_edit += self._get_tracking_log(
                                            material_line_id, data_k, material_line_id.sequence, data_v)
                                    if data_k == 'product_qty':
                                        message_edit += self._get_tracking_log(
                                            material_line_id, data_k, material_line_id.product_qty, data_v)
                                    if data_k == 'product_id':
                                        product_id = self.env['product.template'].sudo().browse(
                                            data_v)
                                        message_edit += self._get_tracking_log(
                                            material_line_id, data_k, material_line_id.product_id.display_name, product_id.display_name)
                                message_edit += '</ul>'
                                message_edit_1 += self.__get_tracking_log_edit(
                                    material_line_id.product_id and material_line_id.product_id.display_name or '', message_edit)
                            if data[0] == 2:
                                material_line_id = product_material_id.material_line_ids.filtered(
                                    lambda ml: ml.id == data[1])
                                message_edit_1 += self.__get_tracking_log_unlink(
                                    material_line_id.product_id and material_line_id.product_id.display_name or '')
                message_edit_1 += '</ul>'
                message += self.__get_tracking_log_edit(
                    product_material_id.name, message_edit_1)
            if vals[0] == 2:
                product_material_id = getattr(self, field).filtered(
                    lambda pm: pm.id == vals[1])
                message += self.__get_tracking_log_unlink(
                    product_material_id.name)
        message += '</li>'
        message += '</ul>'
        return message

    def _set_log_note(self, values):
        self.ensure_one()
        if 'product_material_ids' in values or 'custom_material_ids' in values or 'cup_ids' in values:
            for template in self:
                message = ''
                if 'product_material_ids' in values:
                    message += template.__set_log_note_material(
                        values, 'product_material_ids')
                if 'custom_material_ids' in values:
                    message += template.__set_log_note_material(
                        values, 'custom_material_ids')
                if 'cup_ids' in values:
                    message += template.__set_log_note_cup(
                        values)
                if message != '':
                    template.message_post(body=message)

    @api.model
    def create(self, values):
        # Add code here
        template_id = super(ProductTemplate, self).create(values)
        template_id._set_log_note(values)
        return template_id

#     product_custom_material_ids = fields.Many2many(
#         'product.template',
#         'template_material_rel',
#         'product_tmpl_id',
#         'material_id',
#         string='Product Custom Materials',
#         compute='_compute_product_custom_material', store=False,
#         domain=[('fnb_type', '=', 'topping')])
    parent_code = fields.Char('Parent Code')
    type = fields.Selection(selection=[
        ('product', 'Storable Product'),
        ('service', 'Service')])
    provided_by = fields.Char()
    spoon_id = fields.Many2one(
        'product.template',
        string="Spoon",
        copy=False)

    def name_get(self):
        return [(template.id, '%s%s' % ((template.default_code) and '[%s] ' % (template.ref_code or template.default_code) or '', template.name)) for template in self]

    def action_open_quants(self):
        return self.product_variant_ids.action_open_quants()

#     @api.constrains('default_code')
#     def check_default_code(self):
#         access = self.env['ir.model.access']
#         if not access.check_groups("base.group_erp_manager"):
#             return super(ProductTemplate, self).check_default_code()

#     @api.depends('custom_material_ids')
#     def _compute_product_custom_material(self):
#         for product in self:
#             if product.custom_material_ids:
#                 product.product_custom_material_ids = product.custom_material_ids.mapped('material_id')
#             else:
#                 product.product_custom_material_ids = False

    def write(self, vals):
        self._set_log_note(vals)
        res = super(ProductTemplate, self).write(vals)
        for rcs in self:
            if rcs.categ_id and not rcs.default_code:
                categ_code = rcs.categ_id.get_latest_parent()
                if categ_code == 'Goods':
                    rcs.default_code = self.env['ir.sequence'].next_by_code(
                        'product_goods_code')
                elif categ_code == 'Material':
                    rcs.default_code = self.env['ir.sequence'].next_by_code(
                        'product_material_code')
                elif categ_code == 'Service':
                    rcs.default_code = self.env['ir.sequence'].next_by_code(
                        'product_service_code')
                else:
                    rcs.default_code = self.env['ir.sequence'].next_by_code(
                        'product_other_code')
        return res

    @api.model
    def default_get(self, fields):
        rec = super(ProductTemplate, self).default_get(fields)
        rec.update({
            'categ_id': False,
            'list_price': 0.0,
        })
        return rec

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|', ('name', operator, name),
                      ('default_code', operator, name),
                      ('barcode', operator, name),
                      ('ref_code', operator, name)]
        res = self.search(domain + args, limit=limit)
        return res.name_get()
