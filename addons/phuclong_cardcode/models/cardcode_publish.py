# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, Warning
import base64
import xlrd
import random


class CardcodePublish(models.Model):
    _name = 'cardcode.publish'
    _description = 'Cardcode Publish'
    _order = 'id desc'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(string="Publish Code", required=True)
    publish_date = fields.Date(
        'Date Publish', required=True, default=time.strftime(DEFAULT_SERVER_DATE_FORMAT))
    card_type = fields.Selection([('employee', 'Employee'), ('partner', 'Partner')],
                                 string="Card Type", required=True, default="employee")
    publish_type = fields.Selection([('import', 'Import'), ('random', 'Random')],
                                    string="Publish Type", required=True, default="import")
    file = fields.Binary('File', help='Choose file Excel',
                         readonly=False, copy=False)
    file_name = fields.Char('Filename', size=100, default='Cardcode.xls')
    code_size = fields.Integer('Code Size',)
    alphabet = fields.Integer('Alphabet')
    stand = fields.Integer('Stand')
    quantity = fields.Integer('Quantity')
    prefix = fields.Char('Prefix')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('cancelled', 'Cancelled'),
                              ], string='State', default='draft')
    total_quantity = fields.Float(string="ToTal Quantity",)
    cardcode_line = fields.One2many(
        'cardcode.info', 'publish_id', 'Cardcode Line')
    generate_flag = fields.Boolean('Generated', default=False)

    def unlink(self):
        # Add code here
        self.mapped('cardcode_line').unlink()
        return super(CardcodePublish, self).unlink()


#     @api.onchange('publish_type')
#     def onchange_publish_type(self):
#         for rcs in self:
#             if rcs.publish_type and rcs.cardcode_line:
#                 rcs.cardcode_line.unlink()


    @api.constrains('prefix', 'alphabet', 'code_size')
    def check_code_max_size(self):
        max_size = (len(self.prefix) if self.prefix else 0) + \
            self.alphabet + self.code_size
        if max_size > 13:
            raise UserError(
                _('Total size of code must be smaller than 13 (Prefix + Alphabet + Code Size)'))

    def action_confirmed(self):
        for rcs in self:
            if not rcs.cardcode_line:
                raise Warning(_("Please create the Cardcode Line"))
            rcs.write({'state': 'confirmed'})

    def action_cancel(self):
        for rcs in self:
            if rcs.cardcode_line.filtered(lambda x: x.state == 'using'):
                raise Warning(
                    _("You cannot cancel this card code publish because the card code is using"))
            rcs.cardcode_line.write({'state': 'cancel'})
            rcs.write({'state': 'cancelled'})

    def add_alphabet(self, text, quantum_alphabet, stand):
        test = ""
        check_stand = 0
        list_alphabet = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', 'A',
                         'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Z', 'X', 'C',
                         'V', 'B', 'N', 'M']
        list_stand = []
        if len(str(stand)) > 1:
            for i in str(stand):
                list_stand.append(i)

        if len(list_stand) > 1:
            for i in str(text):
                for y in list_stand:
                    if y == str(check_stand):
                        number = random.randrange(len(list_alphabet))
                        test = test + list_alphabet[number]
                test = test + i
                check_stand = check_stand + 1
        else:
            if(stand > 0):
                for i in str(text):
                    if stand == check_stand:
                        for j in range(0, quantum_alphabet):
                            number = random.randrange(len(list_alphabet))
                            test = test + list_alphabet[number]
                    test = test + i
                    check_stand = check_stand + 1
            else:
                test = text
        return test

    def action_create_cardcode(self):
        for cardcode in self:
            #             if cardcode.publish_type == 'random':
            #                 raise Warning(_("Please set Voucher Amount greater than 0"))
            prefix = cardcode.prefix or ''
#             publish_date = cardcode.publish_date
            if cardcode.cardcode_line:
                cardcode.cardcode_line.unlink()
            if cardcode and cardcode.publish_date:
                size = int(cardcode.code_size)
                size_hidden = int(cardcode.code_size +
                                  len(prefix) + cardcode.alphabet)
                stand = cardcode.stand
                alphabet = cardcode.alphabet
                max_size = 10**size
                if size == 1:
                    min_size = 0
                else:
                    min_size = 10**(size-1)
                max_hidden = 10**size_hidden
                if size == 1:
                    min_hidden = 0
                else:
                    min_hidden = 10**(size_hidden-1)
                quantum = cardcode.quantity
                max_quantum = max_size - min_size
                domain = [
                    ('appear_code', 'like', '%s%%' % prefix),
                    ('size_appear_code', '=', size_hidden),
                ]
                if size > 1:
                    domain.append(
                        ('appear_code', 'not like', '%s0%%' % prefix))
                max_quantum -= self.env['cardcode.info'].sudo().search_count(domain)
                if not cardcode.code_size:
                    raise Warning(
                        _("You can't set None Code Length. We can't create cardcode"))
                elif not quantum:
                    raise Warning(
                        _("You can't set None Quantity. We can't create cardcode"))
                elif(max_quantum < quantum):
                    raise Warning(
                        _("Your code size can't create this cardcode"))
                else:
                    list_size = []
                    list_hidden = []
                    range_list = quantum
                    error = 0
                    while range_list > 0:
                        hidden_code = str(random.randrange(
                            min_hidden, max_hidden)).zfill(size_hidden)
                        if hidden_code in list_hidden:
                            continue
                        code = str(random.randrange(
                            min_size, max_size)).zfill(size)
                        if stand != 0 and alphabet != 0:
                            code = self.add_alphabet(
                                code, alphabet, stand)
                        full_code = prefix + code
                        if full_code in list_size:
                            continue
                        existed_coupon = self.env['cardcode.info'].sudo().search(['|', ('appear_code', '=', full_code), ('hidden_code', '=', hidden_code)],
                                                                                 limit=1)
                        if existed_coupon:
                            error += 1
                            if error <= max_hidden:
                                # print(error, 'existed------')
                                continue
                            else:
                                break
                        list_size.append(full_code)
                        list_hidden.append(hidden_code)
                        vals = {
                            'appear_code': full_code,
                            'hidden_code': hidden_code,
                            'publish_id': cardcode.id,
                            'state': 'create',
                        }
#                         if voucher.type == 'voucher' and voucher.voucher_amount > 0:
#                             vals.update({'voucher_amount':voucher.voucher_amount})
                        self.env['cardcode.info'].create(vals)
#                         list.remove(list[number])
                        range_list -= 1
                vals = {
                    'generate_flag': True,
                }
                cardcode.write(vals)
        return True

    def import_file(self):
        failure = 0
        quantity = 0
        for cardcode in self:
            if cardcode.cardcode_line:
                cardcode.cardcode_line.unlink()
            try:
                recordlist = base64.decodestring(cardcode.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sh = excel.sheet_by_index(0)
            except Exception:
                raise UserError(_('Please select File'))
            if sh:
                messenger = ''
                existed_appear_code = {}
                existed_hidden_code = {}
                for row in range(sh.nrows):
                    if row > 1:
                        print("isinstance(sh.cell(row, 1).value ",
                              isinstance(sh.cell(row, 1).value, float))

                        cardcode_appear_code = sh.cell(row, 1).value and isinstance(sh.cell(row, 1).value, float) \
                            and int(sh.cell(row, 1).value) or sh.cell(row, 1).value or False
                        cardcode_hidden_code = sh.cell(row, 2).value and isinstance(sh.cell(row, 2).value, float) \
                            and int(sh.cell(row, 2).value) or sh.cell(row, 2).value or False
                        if cardcode_appear_code and cardcode_hidden_code and cardcode_appear_code == cardcode_hidden_code:
                            messenger += _('- Error in Line ' +
                                           str(row + 1) + ': Card code is duplicated.\n')
                            failure += 1
                        if cardcode_appear_code:
                            if cardcode_appear_code not in existed_appear_code:
                                existed_appear_code.update(
                                    {cardcode_appear_code: {'line': row + 1}})
                            else:
                                messenger += _(
                                    '- Error in Line ' + str(row + 1) + ': Appear code is repeated at line number: %s.\n') % existed_appear_code[cardcode_appear_code]['line']
                                failure += 1
                            existed_id = self.env['cardcode.info'].search([
                                ('appear_code', '=', str(cardcode_appear_code)),
                                ('publish_id', '!=', cardcode.id)], limit=1)
                            if existed_id:
                                messenger += _('- Error in Line ' + str(row + 1) +
                                               ': Appear code is existed on system.\n')
                                failure += 1
                        if cardcode_hidden_code:
                            if cardcode_hidden_code not in existed_hidden_code:
                                existed_hidden_code.update(
                                    {cardcode_hidden_code: {'line': row + 1}})
                            else:
                                messenger += _(
                                    '- Error in Line ' + str(row + 1) + ': Hidden code is repeated at line number: %s.\n') % existed_hidden_code[cardcode_hidden_code]['line']
                                failure += 1
                            existed_id = self.env['cardcode.info'].search([
                                ('hidden_code', '=', str(cardcode_hidden_code)),
                                ('publish_id', '!=', cardcode.id)], limit=1)
                            if existed_id:
                                messenger += _('- Error in Line ' + str(row + 1) +
                                               ': Hidden code is existed on system.\n')
                                failure += 1
                        vals = {
                            'publish_id': cardcode.id,
                            'appear_code': cardcode_appear_code and str(cardcode_appear_code) or False,
                            'hidden_code': cardcode_hidden_code and str(cardcode_hidden_code) or False,
                            'state': 'create',
                        }
                        if cardcode_appear_code and len(str(cardcode_appear_code)) > 13 or \
                                cardcode_hidden_code and len(str(cardcode_hidden_code)) > 13:
                            messenger += _('- Error in Line ' + str(row + 1) +
                                           ': Total size of code must be smaller than 13.\n')
                            failure += 1

                        if failure <= 0:
                            try:
                                self.env['cardcode.info'].create(vals)
                                quantity += 1
                            except Exception:
                                failure += 1
                                line = row + 1
                                messenger += _('\n- Error in Line ' +
                                               str(line))

                if failure > 0:
                    cardcode.failure = failure or 0
                    raise Warning(_(messenger))

                cardcode.write({'quantity': quantity,
                                'generate_flag': True,
                                })
        return True

    def print_report_cardcode_publish(self):
        return self.env.ref('phuclong_cardcode.report_import_cardcode_publish').report_action(self)

    def action_cardcode_publish_update_date(self):
        action = self.env.ref(
            'phuclong_cardcode.action_cardcode_publish_update_date')
        result = action.read()[0]
        result['context'] = {
            'default_cardcode_publish_id': self.id,
        }
        return result
