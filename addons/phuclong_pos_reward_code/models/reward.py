# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, Warning
import base64
import xlrd
import random


class rewardCodeInfo(models.Model):
    _name = "reward.code.info"

    name = fields.Char('Publish Code', require=True)
    publish_date = fields.Date('Publish Date', require=True)
    state = fields.Selection([
        ('create', 'Created'),
        ('close', 'Closed'),
        ('cancel', 'Canceled')
    ])
    effective_date_from = fields.Date('From Date', require=True)
    effective_date_to = fields.Date('To Date', require=True)
    pos_order_id = fields.Char('Order Reference')
    reward_code_publish_id = fields.Many2one(
        'reward.code.publish',
        'Reward Code Publish', require=True)

    def update_state(self):
        self.state = 'cancel'
        return True

class rewardCodePublish(models.Model):
    _name = "reward.code.publish"

    def _get_default_categ(self):
        domain = []
        categ_id = self.env.ref('besco_product.product_category_3').id
        domain += [('categ_id', '=', categ_id)]
        return domain

    name = fields.Char('Publish Code', require=True)
    publish_date = fields.Date('Publish Date', require=True, default=fields.Date.context_today)
    effective_date_from = fields.Date('From Date', require=True)
    effective_date_to = fields.Date('To Date', require=True)
    product_related_id = fields.Many2one(
        'product.template',
        'Related Product',
        domain=_get_default_categ,
        require=True)
    reward_code_info_ids = fields.One2many(
        'reward.code.info',
        'reward_code_publish_id',
        'Reward Code Info')
    file = fields.Binary(
        'File', help='Choose file Excel', readonly=False, copy=False)
    file_name = fields.Char('Filename', size=100, default='RewardCode.xls')
    prefix = fields.Char('Prefix')
    reward_link = fields.Char()
    description = fields.Char('Description')

    @api.model
    def default_get(self, fields):
        rec = super(rewardCodePublish, self).default_get(fields)
        reward_product = self.env.ref(
            'phuclong_pos_reward_code.reward_code')
        rec.update({
            'product_related_id': reward_product and reward_product.id
        })
        return rec

    def print_template_reward_code_publish(self):
        template = 'phuclong_pos_reward_code.template_reward_code_publish'
        return self.env.ref(template).report_action(self)

    def import_file(self):
        failure = 0
        quantity = 0
        for reward in self:
            # if not reward.prefix:
            #     raise Warning(_('Prefix can not be empty'))
            if not reward.effective_date_from or not reward.effective_date_to:
                raise Warning(_('From Date and To Date can not be empty'))
            try:
                recordlist = base64.decodestring(reward.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sh = excel.sheet_by_index(0)
            except Exception:
                raise UserError(('Please select File'))
            if sh:
                messenger = ''
                for row in range(sh.nrows):
                    if row > 1:
                        prefix = reward.prefix or ''
                        reward_code = sh.cell(row, 1).value
                        if isinstance(reward_code, float):
                            reward_code = int(reward_code)
                            reward_code = str(reward_code)
                            
                        reward_code = prefix + reward_code
                        vals = {
                            'reward_code_publish_id': reward.id,
                            'name': reward_code and str(reward_code) or False,
                            'state': 'create',
                            'effective_date_from': reward.effective_date_from,
                            'effective_date_to': reward.effective_date_to,
                            'publish_date': reward.publish_date
                        }
                        try:
                            # search code before create:
                            code_info_obj = self.env['reward.code.info']
                            code_exist = code_info_obj.search([
                                ('name', '=', str(reward_code)),
                                ('reward_code_publish_id', '=', reward.id)
                            ], limit=1)
                            if not code_exist:
                                code_info_obj.create(vals)
                            else:
                                failure += 1
                                line = int(sh.cell(row, 0).value)
                                messenger += '\n- Record has been exist: %s (STT: %s)' % (str(reward_code), str(line))
                            quantity += 1
                        except Exception:
                            failure += 1
                            line = int(sh.cell(row, 0).value)
                            messenger += '\n- Error in Line ' + str(line)

                if failure > 0:
                    raise Warning(_(messenger))
        return True

    def action_update_effective_date(self):
        action = self.env.ref('phuclong_pos_reward_code.action_update_effective_date')
        result = action.read()[0]
        result['context'] = {
            'default_reward_publish_id': self.id,
            'default_effective_date_from': self.effective_date_from,
            'default_effective_date_to': self.effective_date_to,
        }
        return result
    
    @api.constrains('effective_date_from', 'effective_date_to')
    def _check_point_range(self):
        for publish in self:
            if publish.effective_date_from > publish.effective_date_to:
                raise UserError(_('From Date must smaller than To Date'))
                 
#             effective_date_from_new = publish.effective_date_from
#             effective_date_to_new = publish.effective_date_to
#             compare_publish = self.search([('id', '!=', publish.id),'|', '|','|', 
#                                            ('effective_date_from', '=', effective_date_from_new),
#                                            ('effective_date_to', '=', effective_date_to_new),
#                                            '&',('effective_date_from', '<', effective_date_from_new),('effective_date_to', '>=', effective_date_from_new),
#                                            '&',('effective_date_to', '>', effective_date_from_new),
#                                               '|',('effective_date_from', '<=', effective_date_to_new),('effective_date_to', '<=', effective_date_to_new)])
#             for cp in compare_publish:
#                 if cp.effective_date_from != effective_date_from_new or cp.effective_date_to != effective_date_to_new:
#                     raise UserError(_('''%s is in progress.You can't continue creating new reward code publish !'''%(cp.name)))
        return True
        
#     @api.onchange('effective_date_from', 'effective_date_to')
#     def _onchange_effective_date_from(self):
#         for publish in self:
#             if publish.effective_date_from and publish.effective_date_to:
#                 if publish.effective_date_from > publish.effective_date_to:
#                     raise UserError(_('From Date must smaller than To Date'))
#                     
#                 effective_date_from_new = publish.effective_date_from
#                 effective_date_to_new = publish.effective_date_to
#                 compare_publish = self.search([('id', '!=', publish._origin.id),'|', '|','|', 
#                                                ('effective_date_from', '=', effective_date_from_new),
#                                                ('effective_date_to', '=', effective_date_to_new),
#                                                '&',('effective_date_from', '<', effective_date_from_new),('effective_date_to', '>=', effective_date_from_new),
#                                                '&',('effective_date_to', '>', effective_date_from_new),
#                                                   '|',('effective_date_from', '<=', effective_date_to_new),('effective_date_to', '<=', effective_date_to_new)],limit=1)
#                 if len(compare_publish):
#                     message = _('%s is in progress. Do you want to continue creating new reward code publish?'%(compare_publish.name))
#                     warning = {
#                        'title': _('Warning!'),
#                        'message': message
#                     }
#                     return {'warning': warning}
        
        
        
