# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import base64
import xlrd
from xlrd import open_workbook, xldate_as_tuple
import logging

_logger = logging.getLogger(__name__)


class UpdateLoyaltyExpiredDate(models.Model):
    _name = 'update.loyalty.expired.date'
    _description = 'Update Loyalty Expired Date'

    # def check_values(self, values, create):
    #     return values

    # @api.model
    # def create(self, values):
    #     # Add code here
    #     values = self.check_values(values, True)
    #     return super(UpdateLoyaltyExpiredDate, self).create(values)

    # def write(self, values):
    #     # Add code here
    #     values = self.check_values(values, False)
    #     return super(UpdateLoyaltyExpiredDate, self).write(values)

    name = fields.Char(string='Name', default=lambda self: 'Update Loyalty Expired Date ' +
                       fields.Date.to_string(fields.Date.context_today(self)))
    reason = fields.Char(string='Reason')
    date_done = fields.Datetime(string='Date Done')
    state = fields.Selection(string='State', selection=[(
        'draft', 'Draft'), ('checked', 'Checked'), ('done', 'Done')], default='draft')
    line_ids = fields.One2many(
        comodel_name='update.loyalty.expired.date.line', inverse_name='update_id', string='Lines')

    def button_draft(self):
        for rec in self:
            rec.action_draft()

    def button_checked(self):
        for rec in self:
            rec.action_checked()

    def button_done(self):
        for rec in self:
            rec.action_done()

    def action_draft(self):
        self.ensure_one()
        self.line_ids.filtered(lambda l: l.done).unlink()
        self.write({
            'state': 'draft'
        })

    def action_checked(self):
        self.ensure_one()
        if self.failed > 0:
            self.action_log_failed()
        self.write({
            'state': 'checked'
        })

    def action_done(self):
        self.ensure_one()
        self.line_ids.button_done()
        self.write({
            'state': 'done',
            'date_done': fields.Datetime.now()
        })

    file_data = fields.Binary(
        'File', help="File to check and/or import, raw binary (not base64)")
    file_name = fields.Char('File Name', default="Template")

    failed = fields.Integer(copy=False)
    log_failed = fields.Text(copy=False)

    def print_template(self):
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": '/phuclong_loyalty/static/report/Update_Loyalty_Expired_Date.xls'
        }

    def action_log_failed(self):
        self.ensure_one()
        if not self.log_failed:
            return
        raise ValidationError(self.log_failed)

    def action_read_file(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("The file data do not exits."))
        try:
            line_ids, log_failed, failed = self._read_file_xls()
            if line_ids:
                self.line_ids = [(5,)]
                self.update({'line_ids': line_ids})
            self.update(
                {'failed': failed or 0, 'log_failed': log_failed if failed > 0 else ''})
            if failed == 0:
                self.action_checked()
        except (UserError, ValidationError) as e:
            raise e
        except Exception as e:
            _logger.error(e)
            raise UserError(_("The file must be of extension .xls."))
        return True

    def format_date(self, str_date, book):
        try:
            if isinstance(str_date, float) or isinstance(str_date, int):
                str_date = int(str_date)
                year, month, day, hour, minute, second = xldate_as_tuple(
                    str_date, book.datemode)
                return datetime(year, month, day, hour, minute, second).date()
            return fields.Date.from_string(str_date)
        except Exception as e:
            return False

    def _read_file_xls(self):
        self.ensure_one()
        file_data = base64.decodestring(self.file_data)
        book = open_workbook(file_contents=file_data)
        sheet = book.sheet_by_index(0)

        failed = 0
        log_failed = (_('Failed to read file %s:') % (self.file_name))
        line_ids = []
        partner_obj = self.env['res.partner']
        cardcode_obj = self.env['cardcode.info']
        today = fields.Date.context_today(self)
        for row in range(sheet.nrows):
            if row < 3:
                continue

            error = False
            mess_log = '\n' + _(" + Line %s:" % (int(row + 1)))
            raw_birthday = sheet.cell(row, 1).value
            mobile = sheet.cell(row, 2).value
            appear_code = sheet.cell(row, 3).value
            raw_expired_date = sheet.cell(row, 4).value
            note = sheet.cell(row, 5).value
            birthday = False
            if raw_birthday:
                birthday = self.format_date(raw_birthday, book)
                if not birthday:
                    failed += 1
                    mess_log += '\n' + \
                        _('   - Date of Birth is not right format.')
                    error = True
            expired_date = False
            if raw_expired_date:
                expired_date = self.format_date(raw_expired_date, book)
                if not expired_date:
                    failed += 1
                    mess_log += '\n' + \
                        _('   - Card level expiration date is not right format.')
                    error = True
                elif expired_date <= today:
                    failed += 1
                    mess_log += '\n' + \
                        _('   - Card level expiration date must be greater than today.')
                    error = True
            else:
                failed += 1
                mess_log += '\n' + \
                    _('   - Card level expiration date is required.')
                error = True
            if not appear_code:
                failed += 1
                mess_log += '\n' + _('   - Card code is required.')
                error = True
            if mobile:
                partner_id = partner_obj.search([('mobile', '=', mobile)])
                if partner_id:
                    if len(partner_id) == 1:
                        if appear_code:
                            if not partner_id.appear_code_id or partner_id.appear_code_id.appear_code != appear_code:
                                failed += 1
                                mess_log += '\n' + \
                                    _('   - Card code does not belong to customer %s.') % partner_id.display_name
                                error = True
                    else:
                        failed += 1
                        mess_log += '\n' + _('   - Mobile %s belongs to %s customer %s.') % (
                            mobile, len(partner_id), ', '.join([x for x in partner_id.mapped('display_name')]))
                        error = True
                else:
                    failed += 1
                    mess_log += '\n' + _('   - Mobile is not existed.')
                    error = True
            else:
                failed += 1
                mess_log += '\n' + _('   - Mobile is required.')
                error = True
            if not error:
                line_ids.append((0, 0, {
                    'partner_id': partner_id.id,
                    'expired_date': expired_date,
                    'birthday': birthday,
                    'note': note
                }))
            else:
                log_failed += mess_log

        return line_ids, log_failed, failed


class UpdateLoyaltyExpiredDateLine(models.Model):
    _name = 'update.loyalty.expired.date.line'
    _description = 'Update Loyalty Expired Date Line'

    update_id = fields.Many2one(
        comodel_name='update.loyalty.expired.date', string='Update')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Partner')
    mobile = fields.Char(string='Mobile', related='partner_id.mobile')
    appear_code_id = fields.Many2one(
        'cardcode.info', string='Appear Code', related='partner_id.appear_code_id')
    expired_date = fields.Date(string='Card level expiration date')
    birthday = fields.Date(string='Date of Birth')
    note = fields.Text(string='Note')
    log = fields.Text(string='Log', readonly=True)
    done = fields.Boolean(string='Done?')

    def button_done(self):
        for rec in self:
            if not rec.done:
                rec.action_done()

    def action_done(self):
        self.ensure_one()
        try:
            result = False
            if self.partner_id and self.expired_date:
                values = {
                    'expired_date': self.expired_date
                }
                if self.birthday:
                    values.update({
                        'birthday': self.birthday
                    })
                result = self.sudo().partner_id.write(values)
            if result:
                self.write({
                    'done': True,
                    'log': _('Success')
                })
            else:
                self.write({
                    'log': _('Cannot modify client.')
                })
            self._cr.commit()
        except Exception as e:
            self._cr.rollback()
            self.write({
                'log': str(e)
            })
            self._cr.commit()
            pass
