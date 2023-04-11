# -*- coding: utf-8 -*-
from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    mobile = fields.Char(tracking=True)
    phone = fields.Char(tracking=True)

    @api.constrains('active', 'mobile', 'phone')
    def _check_active_unique_mobile_phone(self):
        for rec in self:
            if rec.active:
                if rec.mobile:
                    if self.with_user(SUPERUSER_ID).search_count([('active', '=', True), ('id', '!=', rec.id), ('mobile', '=', rec.mobile)]):
                        raise ValidationError(_("Mobile must be unique!"))
                if rec.phone:
                    if self.with_user(SUPERUSER_ID).search_count([('active', '=', True), ('id', '!=', rec.id), ('phone', '=', rec.phone)]):
                        raise ValidationError(_("Phone must be unique!"))

    def _compute_pos_order_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        pos_order_groups = self.env['pos.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )
        partners = self.browse()
        for group in pos_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.pos_order_count += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
        (self - partners).write({
            'pos_order_count': 0
        })

    @api.depends('pos_order_ids')
    def _compute_nearest_order_date(self):
        for partner in self:
            nearest_order_date = False
            if partner.pos_order_ids:
                lasted_order = self.env['pos.order'].sudo().search(
                    [('partner_id', '=', partner.id), ('state', '=', 'paid')], order='id desc')
                if lasted_order:
                    nearest_order_date = lasted_order[0].date_order
            partner.nearest_order_date = nearest_order_date

    expired_date = fields.Date('Card level expiration date')
    change_date_level = fields.Date('Card level change date')
    #appearcode = fields.Char('Appear card code')
    wallet_on_account = fields.Float('On account')
    payment_pos_order_ref = fields.Char('Lasted Payment Ref', readonly=True)
    pos_order_count = fields.Integer(
        compute='_compute_pos_order_count',
        string='POS Order Count')
    pos_order_ids = fields.One2many('pos.order', 'partner_id', 'POS Order')
    is_default_vendor = fields.Boolean('Default Vendor', default=False)
    total_point_act = fields.Float('Available Point', readonly=False)
    current_point_act = fields.Float('Total Point', readonly=False)
    pos_note = fields.Char('POS Note')
    use_for_on_account = fields.Boolean(
        'Use For On Account Partner', default=False)
    nearest_order_date = fields.Datetime(
        compute='_compute_nearest_order_date', readonly=True, store=True)

#     @api.model
    def get_on_acount_amount(self):
        return self.wallet_on_account or 0

    @api.model
    def update_partner_on_account_amount(self, partner_list, order_name):
        updated_partner = self.search(
            [('payment_pos_order_ref', '=', order_name)], limit=1) or False
        if updated_partner:
            return True

        update_list = []
        # Check first
        for partner in partner_list:
            partner_id = self.browse(partner[0])
            amount_update = partner[1]
            if partner_id:
                amount_available = partner_id.wallet_on_account
                if amount_update > amount_available:
                    return partner_id.wallet_on_account
            update_list.append([partner_id, amount_available-amount_update])

        # Update later
        for list in update_list:
            partner_update = list[0]
            partner_update.with_user(SUPERUSER_ID).write(
                {'wallet_on_account': list[1], 'payment_pos_order_ref': order_name})

        return True

    @api.onchange('supplier')
    def _onchange_supplier_vendor(self):
        for rcs in self:
            if not rcs.supplier:
                rcs.is_default_vendor = False

    @api.constrains('wallet_on_account',)
    def _check_sequence(self):
        for rcs in self:
            if rcs.wallet_on_account < 0:
                raise UserError(_('The value input cannot be less than 0!'))

    @api.constrains('is_default_vendor',)
    def _check_default_vendor(self):
        for rcs in self:
            if rcs.supplier and rcs.is_default_vendor:
                domain = [('supplier', '=', True),
                          ('is_default_vendor', '=', True),
                          ('id', '!=', rcs.id)]
                partner_vendor = self.search(domain)
                if partner_vendor:
                    raise UserError(_("Default vendor have already %s-%s") % (partner_vendor.ref,
                                                                              partner_vendor.name))

    @api.model
    def check_create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        error_mess = ''
        if partner.get('image'):
            partner['image'] = partner['image'].split(',')[1]

        partner_id = partner.pop('id', False)
        if partner_id:  # Modifying existing partner
            if partner.get('mobile', False):
                exist_partner_id = self.env['res.partner'].search(
                    [('mobile', '=', partner.get('mobile')), ('id', '!=', partner_id)], limit=1)
                if len(exist_partner_id):
                    error_mess = _(
                        "The Mobile number is already exist in system. Please check again !!")

            if partner.get('phone', False):
                exist_partner_id = self.env['res.partner'].search(
                    [('phone', '=', partner.get('phone')), ('id', '!=', partner_id)], limit=1)
                if len(exist_partner_id):
                    error_mess = _(
                        "The Phone number is already exist in system. Please check again !!")

#             if partner.get('email', False):
#                 exist_partner_id = self.env['res.partner'].search([('email','=',partner.get('email')),('id','!=',partner_id)], limit=1)
#                 if len(exist_partner_id):
#                     error_mess = _("The Email is already exist in system. Please check again !!")
            if error_mess != '':
                #                 self.browse(partner_id).write(partner)
                #                 return partner_id
                #             else:
                return error_mess
        else:
            if partner.get('mobile', False):
                if not partner.get('mobile').replace('(\[(.*?)\])', '').replace(' ', '').isdigit():
                    error_mess = 'Số điện thoại %s không được nhập kí tự khác số' % (
                        partner.get('mobile'))
                exist_partner_id = self.env['res.partner'].search(
                    [('mobile', '=', partner.get('mobile'))], limit=1)
                if len(exist_partner_id):
                    error_mess = _(
                        "The Mobile number is already exist in system. Please check again !!")

            if partner.get('phone', False):
                exist_partner_id = self.env['res.partner'].search(
                    [('phone', '=', partner.get('phone'))], limit=1)
                if len(exist_partner_id):
                    error_mess = _(
                        "The Phone number is already exist in system. Please check again !!")

#             if partner.get('email', False):
#                 exist_partner_id = self.env['res.partner'].search([('email','=',partner.get('email'))], limit=1)
#                 if len(exist_partner_id):
#                     error_mess = _("The Email is already exist in system. Please check again !!")
            partner['lang'] = self.env.user.lang
            partner['customer'] = True
            if error_mess != '':
                #                 partner_id = self.create(partner).id
                #                 return partner_id
                #             else:
                return error_mess
        return True
