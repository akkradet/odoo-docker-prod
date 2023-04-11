# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import datetime, timedelta, date as datetime_date
from dateutil.relativedelta import relativedelta

from dateutil.relativedelta import relativedelta
import pytz

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _get_prefix_suffix(self, date=None, date_range=None):
        def _interpolate(s, d):
            return (s % d) if s else ''

        def _interpolation_dict():
            now = range_date = effective_date = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
#             if self._context.get('ir_sequence_date'):
#                 effective_date = datetime.strptime(self._context.get('ir_sequence_date'), '%Y-%m-%d')
#             if self._context.get('ir_sequence_date_range'):
#                 range_date = datetime.strptime(_(self._context.get('ir_sequence_date_range')), '%Y-%m-%d')
            if self._context.get('ir_sequence_date'):
                effective_date = fields.Datetime.from_string(self._context.get('ir_sequence_date'))
            if self._context.get('ir_sequence_date_range'):
                range_date = fields.Datetime.from_string(self._context.get('ir_sequence_date_range'))
            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }
            res = {}
            for key, format in sequences.items():
                res[key] = effective_date.strftime(format)
                res['range_' + key] = range_date.strftime(format)
                res['current_' + key] = now.strftime(format)

            return res

        d = _interpolation_dict()
        ### update d vs context da dc truyen tu ben create stock.picking
        d.update(self._get_prefix_suffix_inherit())
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence \'%s\'') % (self.get('name')))
        return interpolated_prefix, interpolated_suffix

    def get_next_char(self, number_next):
        interpolated_prefix, interpolated_suffix = self._get_prefix_suffix()
        
        type_standard = False
        if not number_next:
            type_standard = True
            if self._context.get('ir_sequence_date', False):
                transaction_date = datetime.strptime(self._context['ir_sequence_date'], '%Y-%m-%d')
                day = int(transaction_date.strftime('%d'))
                month = int(transaction_date.strftime('%m'))
                year = int(transaction_date.strftime('%Y'))
            else:
                today = self.env['res.users']._convert_user_datetime(fields.Datetime.now())
                day = int(today.strftime('%d'))
                month = int(today.strftime('%m'))
                year = int(today.strftime('%Y'))
            
            #THANH: use context for cron job pass transaction company to generate sequence (in multi company)
            if self._context.get('transaction_company_id',False):
                company_id = self._context['transaction_company_id']
            else:
                company_id = self.company_id and self.company_id.id or self.env.user.company_id.id
            
            sql = "select his.number_current from ir_sequence_his his where his.seq_id=%s and company_id=%s"%(self.id, company_id)
            #THANH: filter by company_analytic_account_id
            if self._context.get('company_analytic_account_id',False):
                company_analytic_account_id = self._context['company_analytic_account_id']
                sql += ' and company_analytic_account_id=%s'%(company_analytic_account_id)
            else:
                company_analytic_account_id = 'null'
            
            if self.rollback_rule == 'Yearly':
                sql += " AND his.year = %s" % (year)
            if self.rollback_rule == 'Monthly':
                sql += " AND his.year = %s AND his.month = %s" % (year, month)
            if self.rollback_rule == 'Daily':
                sql += " AND his.year = %s AND his.month = %s AND his.day = %s" % (year, month, day)
            
            # THANH - add FOR UPDATE to force comming action wait sql insert into ir_sequence_his commit
            # help to prevent duplicate sequence number
            sql = sql + ' order by his.number_current desc limit 1 FOR UPDATE;'
            self.env.cr.execute(sql)
            result = self.env.cr.fetchone()
            if result and result[0] != 0:
                number_current = result[0]
                number_next = number_current + self.number_increment
            else:
                number_next = self.number_next
                
        sequence = interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix 
        #Thanh: Insert into History
        if type_standard:
            self.env.cr.execute('''
                        INSERT INTO ir_sequence_his (create_uid,create_date,write_uid,write_date,
                            seq_id,generate_code, company_analytic_account_id, company_id,
                            number_current, day,month,year)
                        VALUES (%s,current_timestamp,%s,current_timestamp,
                                %s,'%s',
                                %s, %s,
                                %s, %s, %s, %s);
            '''%(self.env.user.id, self.env.user.id, 
                 self.id, sequence, 
                 company_analytic_account_id, company_id, 
                 number_next, day, month, year))
        # Thanh: Insert into History
        return sequence
