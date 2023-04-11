# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class updateRewardEffectiveDate(models.TransientModel):
    _name = "wizard.update.reward.publish"

    reward_publish_id = fields.Many2one('reward.code.publish', string='Reward Code Publish')
    effective_date_from = fields.Date('From Date', require=True)
    effective_date_to = fields.Date('To Date', require=True)
    update_for_publish = fields.Boolean(
        'Update for this Reward Code Publish',
        default=True)

    @api.onchange('effective_date_from', 'effective_date_to')
    def _onchange_effective_date_from(self):
        publish = self.reward_publish_id
        min_form_date = self.reward_publish_id.effective_date_from
        min_to_date = self.reward_publish_id.effective_date_to

        if self.effective_date_from < min_form_date or self.effective_date_to < min_to_date:
            message = _("The new effective date must be greater than the current one")
            warning = {
               'title': _('Warning!'),
               'message': message
            }
            self.effective_date_from = min_form_date
            self.effective_date_to = min_to_date
            return {'warning': warning}
        
#         if self.effective_date_from and self.effective_date_to:
#             effective_date_from_new = self.effective_date_from
#             effective_date_to_new = self.effective_date_to
#             compare_publish = self.env['reward.code.publish'].search([('id', '!=', publish.id),'|', '|','|', 
#                                            ('effective_date_from', '=', effective_date_from_new),
#                                            ('effective_date_to', '=', effective_date_to_new),
#                                            '&',('effective_date_from', '<', effective_date_from_new),('effective_date_to', '>=', effective_date_from_new),
#                                            '&',('effective_date_to', '>', effective_date_from_new),
#                                               '|',('effective_date_from', '<=', effective_date_to_new),('effective_date_to', '<=', effective_date_to_new)],limit=1)
#             if len(compare_publish):
#                 message = _('%s is in progress. Do you want to continue creating new reward code publish?'%(compare_publish.name))
#                 warning = {
#                    'title': _('Warning!'),
#                    'message': message
#                 }
#                 return {'warning': warning}

    def update_effective_date(self):
        publish = self.reward_publish_id
        for rcs in self:
#             if self.effective_date_from and self.effective_date_to:
#                 effective_date_from_new = self.effective_date_from
#                 effective_date_to_new = self.effective_date_to
#                 compare_publish = self.env['reward.code.publish'].search([('id', '!=', publish.id),'|', '|','|', 
#                                                ('effective_date_from', '=', effective_date_from_new),
#                                                ('effective_date_to', '=', effective_date_to_new),
#                                                '&',('effective_date_from', '<', effective_date_from_new),('effective_date_to', '>=', effective_date_from_new),
#                                                '&',('effective_date_to', '>', effective_date_from_new),
#                                                   '|',('effective_date_from', '<=', effective_date_to_new),('effective_date_to', '<=', effective_date_to_new)])
#                 for cp in compare_publish:
#                     if cp.effective_date_from != effective_date_from_new or cp.effective_date_to != effective_date_to_new:
#                         raise UserError(_('''%s is in progress.You can't continue creating new reward code publish !'''%(cp.name)))
            if rcs.reward_publish_id:
                vals = {
                    'effective_date_from': self.effective_date_from,
                    'effective_date_to': self.effective_date_to,
                }
                rcs.reward_publish_id.reward_code_info_ids.write(vals)
                if rcs.update_for_publish:
                    rcs.reward_publish_id.write(vals)
        return
