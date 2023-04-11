# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def name_get(self):
        if not self._context.get('with_appear_code', False):
            return super(ResPartner, self).name_get()
        res = []
        for partner in self:
            if partner.appear_code_id:
                name = '%s [%s]' % (
                    partner.name, partner.appear_code_id.display_name)
            else:
                name = partner.name
            res.append((partner.id, name))
        return res

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    appear_code_id = fields.Many2one(
        'cardcode.info', string='Appear Code', readonly=False, search=False)
    cardcode_histoy_ids = fields.One2many(
        'cardcode.history', 'partner_id', string="Card Code History", readonly=True)

    def action_update_cardcode(self):
        action = self.env.ref(
            'phuclong_cardcode.action_wizard_cardcode_history_info')
        result = action.read()[0]
        result['context'] = {'default_partner_id': self.id,
                             #  'default_cardcode_id': self.appear_code_id and self.appear_code_id.id or False,
                             'default_cardcode_old_id': self.appear_code_id and self.appear_code_id.id or False}
        return result

    @api.constrains('appear_code_id')
    def check_card_code_unique(self):
        for partner in self:
            if partner.appear_code_id:
                # if partner.appear_code_id.state != 'create' or partner.appear_code_id.card_type != 'partner':
                    # raise UserError(_('Cardcode is not available: %s' % (
                    #     partner.appear_code_id.appear_code)))
                partner_has_code = self.search(
                    [('id', '!=', partner.id), ('appear_code_id', '=', partner.appear_code_id.id)], limit=1)
                if len(partner_has_code):
                    raise UserError(_('This cardcode has belong to another customer: %s (%s)' % (
                        partner_has_code.name, partner_has_code.mobile)))

    def check_partner_appear_code(self, vals, create=True):
        if 'appear_code_id' in vals:
            appear_code_id = self.env['cardcode.info'].search(
                [('id', '=', int(vals.get('appear_code_id', 0)))], limit=1)
            if appear_code_id:
                if appear_code_id.card_type != 'partner':
                    raise UserError(
                        _('Cardcode is not available: %s' % (appear_code_id.appear_code)))
                if create:
                    if appear_code_id.state != 'create' or appear_code_id.partner_id:
                        raise UserError(
                            _('Cardcode is not available: %s' % (appear_code_id.appear_code)))
                else:
                    for partner in self:
                        if partner.appear_code_id != appear_code_id:
                            if appear_code_id.state != 'create' or appear_code_id.partner_id:
                                raise UserError(
                                    _('Cardcode is not available: %s' % (appear_code_id.appear_code)))

    def using_appear_code(self, vals, create=True):
        if 'appear_code_id' in vals:
            for rec in self:
                if rec.appear_code_id:
                    rec.appear_code_id.write(
                        {'partner_id': rec.id, 'state': 'using'})

    def unused_appear_code(self, vals):
        if 'appear_code_id' in vals and self._context.get('import_file', False):
            for rec in self:
                if rec.appear_code_id:
                    rec.appear_code_id.write(
                        {'partner_id': False, 'state': 'create'})

    def button_unused_appear_code(self):
        for rec in self:
            if rec.appear_code_id:
                rec.appear_code_id.write(
                    {'partner_id': False, 'state': 'create'})
#                 if self._context.get('remove_appear_code', False):
                self._cr.execute(
                    'UPDATE res_partner SET appear_code_id = null where id = %s' % (rec.id))

    @api.model
    def create(self, vals):
        self.check_partner_appear_code(vals, True)
        res = super(ResPartner, self).create(vals)
        res.using_appear_code(vals, True)
        return res

    def write(self, vals):
        self.check_partner_appear_code(vals, False)
        self.unused_appear_code(vals)
        result = super(ResPartner, self).write(vals)
        self.using_appear_code(vals, False)
        return result
