# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from odoo.exceptions import UserError
import base64
import xlrd
from xlrd import open_workbook
from odoo.loglevels import ustr
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class LoyaltyPointHistory(models.Model):
    _inherit = 'loyalty.point.history'
    _order = 'id desc'

    @api.depends('prior_total_point_act', 'current_total_point_act')
    def _compute_loyalty_level(self):
        for record in self:
            level_before = False
            level_after = False
            is_downgrade_from_import = False
            self._cr.execute('''
                SELECT id FROM loyalty_level 
                WHERE from_point_act <= %s AND to_point_act >= %s AND active = true
                ''' % (record.prior_total_point_act, record.prior_total_point_act))
            res = self._cr.fetchone()
            if not res:
                record.prior_loyalty_level = False
            else:
                level_before = res
                record.prior_loyalty_level = level_before

            self._cr.execute('''
                SELECT id FROM loyalty_level 
                WHERE from_point_act <= %s AND to_point_act >= %s AND active = true
                ''' % (record.current_total_point_act, record.current_total_point_act))
            res = self._cr.fetchone()
            if not res:
                record.current_loyalty_level = False
            else:
                level_after = res
                record.current_loyalty_level = level_after

            if level_before != level_after:
                bill_date = record.bill_date or fields.Datetime.now()
                vals = {'change_date_level': bill_date}
#                 if not level_before:
#                     vals.update({'change_date_level':record.bill_date})
                point_level_before = 0
                if level_before:
                    level_before_id = self.env['loyalty.level'].browse(
                        level_before)
                    point_level_before = level_before_id.from_point_act
                if level_after:
                    level_after_id = self.env['loyalty.level'].browse(
                        level_after)
                    if level_after_id:
                        #                         record.method = 'upgrade'
                        if level_after_id.from_point_act > point_level_before:
                            self._cr.execute('''
                                UPDATE loyalty_point_history SET method = 'upgrade'
                                WHERE id = %s''' % (record.id))
                        if level_after_id.from_point_act < point_level_before:
                            if not record.import_id:
                                self._cr.execute('''
                                UPDATE loyalty_point_history SET method = 'downgrade'
                                WHERE id = %s''' % (record.id))
                            else:
                                is_downgrade_from_import = True
                        if level_after_id.effective_time:
                            expired_date = bill_date.date() + \
                                relativedelta(
                                    months=level_after_id.effective_time)
                            vals.update({'expired_date': expired_date})
                        else:
                            vals.update({'expired_date': False})
                if not record.not_update_partner and not is_downgrade_from_import:
                    record.partner_id.write(vals)
                record.is_downgrade_from_import = is_downgrade_from_import
        return True

    @api.depends('bill_id', 'order_type')
    def _compute_pos_order(self):
        for record in self:
            if record.bill_id and record.order_type == 'POS Order':
                record.pos_order_id = record.bill_id
                record.warehouse_id = record.pos_order_id.warehouse_id
            else:
                record.pos_order_id = False
                record.warehouse_id = False

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domains = []
        domain = domain or []
        if not self._context.get('from_search_warehouse_id', False):
            for dom in domain:
                if len(dom) == 3:
                    if dom[0] == 'warehouse_id' and dom[1] == 'not ilike':
                        domains.append(['id', 'not in', self.search(
                            [("warehouse_id", "ilike", dom[2])]).ids])
                        continue
                domains.append(dom)
        return super(LoyaltyPointHistory, self.with_context(from_search_warehouse_id=True)).search_read(domains, fields, offset, limit, order)

    prior_loyalty_level = fields.Many2one(
        'loyalty.level', string="Prior Loyalty Level", compute='_compute_loyalty_level', store=True, readonly=True)
    current_loyalty_level = fields.Many2one(
        'loyalty.level', string="Current Loyalty Level", compute='_compute_loyalty_level', store=True, readonly=True)
    pos_order_id = fields.Many2one(
        'pos.order', string="POS Order Ref", compute='_compute_pos_order', store=True, readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', compute='_compute_pos_order', search=None, store=True, readonly=True)
    method = fields.Selection([('upgrade', 'Upgrade'), ('downgrade', 'Downgrade'), ('maintain', 'Maintain'), ('locked', 'Locked')],
                              string="Method", default=False)
    is_downgrade_from_import = fields.Boolean(
        string='Is Downgrade From Import?', compute='_compute_loyalty_level', store=True, readonly=True)
    not_update_partner = fields.Boolean(
        string='Not Update Partner?', compute=False, store=True, readonly=True)
    bill_amount = fields.Float(string='Bill Amount', digits=(16, 0))
    exchange_point = fields.Float('Exchange Point', digits=(16, 0))
    # Điểm tích lũy cộng dồn trước đó
    prior_point_act = fields.Float('Prior Available Point', digits=(16, 0))
    # Điểm tích lũy cộng dồn = tổng điểm trước đó + exchange point
    current_point_act = fields.Float('Current Available Point', digits=(16, 0))
    prior_total_point_act = fields.Float('Prior Total Point', digits=(16, 0))
    current_total_point_act = fields.Float(
        'Current Total Point', digits=(16, 0))
    more_info = fields.Char('More Information')
    partner_id = fields.Many2one(inverse='_inverse_partner_id')
    appear_code_id = fields.Many2one(
        'cardcode.info', string='Appear Code', readonly=True, related='partner_id.appear_code_id')

    def _inverse_partner_id(self):
        for rec in self.sudo():
            if rec.partner_id:
                rec.current_change_date_level = rec.partner_id.change_date_level
                rec.current_expired_date = rec.partner_id.expired_date
            else:
                rec.current_change_date_level = False
                rec.current_expired_date = False

    current_change_date_level = fields.Date(string='Current Change Date Level')
    current_expired_date = fields.Date(string='Current Expired Date')

    @api.model
    def create(self, values):
        # Add code here
        if self._context.get('not_update_partner', False):
            values.update({'not_update_partner': True})
        return super(LoyaltyPointHistory, self).create(values)

    @api.model
    def cron_downgrade_loyalty_level(self, ids=None):
        #         current_date = time.strftime(DATE_FORMAT)
        current_date = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()).date()
        expired_partner = self.env['res.partner'].search(
            [('expired_date', '!=', False), ('expired_date', '<', current_date), ('card_code_pricelist_id', '=', False), ('use_for_on_account', '=', False)])
        for partner in expired_partner:
            point_his = self.env['loyalty.point.history'].search(
                [('partner_id', '=', partner.id)], order='id desc', limit=1)
            if point_his and point_his.method == 'locked':
                continue

            loyalty_level_id = partner.loyalty_level_id or False
            if not loyalty_level_id:
                partner.write({'expired_date': False})
                continue

            expired_date = False
            method = False
            total_point_act_before = partner.total_point_act
            current_point_act_before = partner.current_point_act
            current_point_act_after = 0
            if partner.current_point_act >= loyalty_level_id.minimum_point:
                method = 'maintain'
                if loyalty_level_id.effective_time:
                    expired_date = partner.expired_date + \
                        relativedelta(months=loyalty_level_id.effective_time)
                current_point_act_after = loyalty_level_id.from_point_act
            else:
                if loyalty_level_id.downgrade_method == 'down':
                    method = 'downgrade'
                    level_down = self.env['loyalty.level'].search(
                        [('to_point_act', '<', loyalty_level_id.from_point_act)], order='to_point_act desc', limit=1)
                    if level_down:
                        current_point_act_after = level_down.from_point_act
                        if level_down.effective_time:
                            expired_date = partner.expired_date + \
                                relativedelta(months=level_down.effective_time)
                    else:
                        if loyalty_level_id.from_point_act == 0 and loyalty_level_id.effective_time:
                            expired_date = partner.expired_date + \
                                relativedelta(
                                    months=loyalty_level_id.effective_time)
                else:
                    method = 'locked'
                    expired_date = partner.expired_date
#                     loyalty_level_zero_id = self.env['loyalty.level'].search(
#                         [('from_point_act', '=', 0)], limit=1)
#                     if loyalty_level_zero_id and loyalty_level_zero_id.effective_time:
#                         expired_date = partner.expired_date + \
#                             relativedelta(
#                                 months=loyalty_level_zero_id.effective_time)
#                     if partner.appear_code_id:
#                         partner.appear_code_id.write({'state': 'close',
#                                                       'date_expired': partner.expired_date})
            expired_date_before = partner.expired_date
            expired_date_before = expired_date_before.strftime(
                "%Y-%m-%d 16:59:59")

            partner_vals = {
                'expired_date': expired_date,
                'current_point_act': current_point_act_after,
                'total_point_act': 0
            }
            partner.write(partner_vals)
            vals = {
                'partner_id': partner.id,
                'mobile': partner.mobile,
                'bill_id': 0,
                'bill_amount': 0,
                'bill_date': expired_date_before,
                'order_type': 'POS Order',
                'exchange_point': -total_point_act_before if total_point_act_before else 0,
                'point_down': -total_point_act_before if total_point_act_before else 0,
                'prior_point_act': total_point_act_before,
                'current_point_act': 0,
                'prior_total_point_act': current_point_act_before,
                'current_total_point_act': current_point_act_after,
                'method': method,
            }
            self.env['loyalty.point.history'].create(vals)
        return True


class LoyaltyPointHistoryImport(models.Model):
    _inherit = 'loyalty.point.history.import'

    include_prior_point_act = fields.Boolean(
        'Update Available Point', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('validated', 'Validated'),
        ('done', 'Done')
    ], string='State', default='draft')
    date_done = fields.Datetime(string='Date Done')

    def check_file_import(self):
        today = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()).date()
        for record in self:
            if record.state == 'done':
                return
            partner_obj = self.env['res.partner']
            if record.import_line_ids:
                for line in record.import_line_ids:
                    self._cr.execute(
                        '''DELETE FROM loyalty_point_history WHERE id = %s''' % (line.id))
            try:
                recordlist = base64.decodestring(self.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sh = excel.sheet_by_index(0)
            except Exception:
                raise UserError(('Please select File'))
            if sh:
                for row in range(3, sh.nrows):
                    row_values = sh.row_values(row)
                    error = 'true'
                    note = ''
                    name = row_values[0]
                    date = row_values[1]
                    mobile = row_values[2]
                    if isinstance(mobile, float) or isinstance(mobile, int):
                        mobile = int(mobile)
                        mobile = str(mobile)
                    mobile = mobile.replace(" ", "")
                    point = row_values[3]
                    if not name:
                        error = 'error'
                        note += _(' ,Name are required: ') + mobile
                    if not mobile:
                        error = 'error'
                        note += _(' ,Mobile are required: ') + name
                    else:
                        try:
                            mobile_head = int(mobile[0])
                            if mobile_head != 0:
                                error = 'error'
                                note += _(' ,Mobile is not right format: ') + mobile
                        except:
                            error = 'error'
                            note += _(' ,Mobile is not right format: ') + mobile
                    try:
                        point = float(point)
                    except Exception:
                        error = 'error'
                        note += _(' ,Point column is not in float format: ') + \
                            str(point)
                    partner_id = partner_obj.search([('mobile', '=', mobile)])
                    if not partner_id:
                        error = 'error'
                        note += _(' ,Mobile is not existed: ') + name
                    try:
                        if partner_id.card_code_pricelist_id or partner_id.use_for_on_account:
                            error = 'error'
                            note += _(' ,Customer is not allowed to import loyalty point: ') + \
                                partner_id.display_name
                        else:
                            if partner_id.expired_date and partner_id.expired_date < today:
                                error = 'error'
                                note += _(' ,Customer have expired Loyalty: ') + \
                                    partner_id.display_name
                            else:
                                if (partner_id.current_point_act + point) < 0 or (record.include_prior_point_act and (partner_id.total_point_act + point) < 0):
                                    error = 'error'
                                    note += _(' ,Please check customer point: ') + \
                                        partner_id.display_name
                                if date:
                                    date = datetime.strptime(
                                        str(date), "%Y-%m-%d").strftime("%Y-%m-%d")
                                    check_date = datetime.strptime(
                                        str(date), "%Y-%m-%d")
                                    if check_date.year < 1900:
                                        error = 'error'
                                        note += _(' ,Year of birthday much be after 1900: ') + \
                                            str(date)
                    except Exception:
                        error = 'error'
                        note += _(' ,Birthday is not right format: ') + \
                            str(date)
                    if error == 'error' or note != '':
                        record.import_line_ids.create({
                            'error': error,
                            'note': note,
                            'mobile': mobile,
                            'import_id': record.id,
                        })
                record.write({'state': 'checked'})
                if not record.import_line_ids:
                    warning_mess = {'title': _('Check file complete'),
                                    'message': _('''Everything seem valid, Validate to confirm import''')}
                    return {'warning': warning_mess}

    def validate_import(self):
        for record in self:
            if record.state == 'draft':
                raise UserError(_('''Please check file before import'''))
            if record.import_line_ids:
                for line in record.import_line_ids:
                    if line.error == 'error':
                        raise UserError(
                            _('''Please check error line before begin import'''))
            record.write({'state': 'validated'})
        return True

    def action_import_done(self):
        for record in self:
            if record.state == 'done':
                return
            partner_obj = self.env['res.partner']
            if record.state == 'draft':
                raise UserError(_('''Please check file before import'''))
            if record.import_line_ids:
                for line in record.import_line_ids:
                    if line.error == 'error':
                        raise UserError(
                            _('''Please check error line before begin import'''))
                    else:
                        return
                self._cr.execute('''DELETE FROM loyalty_point_history WHERE import_id = %s
                    ''' % (record.id))
            try:
                recordlist = base64.decodestring(self.file)
                excel = xlrd.open_workbook(file_contents=recordlist)
                sh = excel.sheet_by_index(0)
            except Exception as e:
                raise UserError(_(str(e)))
            if sh:
                count = 1
                for row in range(3, sh.nrows):
                    note = ''
                    row_values = sh.row_values(row)
                    error = 'true'
                    vals_partner = {}
                    name = row_values[0]
                    date = row_values[1]
                    mobile = row_values[2]
                    if isinstance(mobile, float) or isinstance(mobile, int):
                        mobile = int(mobile)
                        mobile = str(mobile)
                    mobile = mobile.replace(" ", "")
                    point = row_values[3] and int(row_values[3]) or 0
                    more_info = row_values[4]
                    if date:
                        date = datetime.strptime(
                            str(date), "%Y-%m-%d").strftime("%Y-%m-%d")
                    partner = partner_obj.search(
                        [('mobile', '=', mobile)], limit=1)
#                     partner = partner_obj.browse(partner_id[0])
                    prior_point_act = 0.0
                    total_point_act = 0.0

                    total_prior_point_act = 0.0
                    current_point_act = 0.0
                    try:
                        if not len(partner):
                            #                 output.write(str(mobile) + '\n')
                            total_point_act = point if record.include_prior_point_act else 0
                            current_point_act = point
                            vals_partner.update({
                                'name': name,
                                'mobile': mobile,
                                'customer': True,
                                'current_point_act': current_point_act or 0.0,
                                'total_point_act': total_point_act or 0.0,
                            })
                            if date:
                                vals_partner.update({
                                    'birthday': date or False,
                                })
                            partner = partner_obj.create(vals_partner)
#                             print('Create Partner: ' + str(count))
                        else:
                            prior_point_act = partner.total_point_act
                            total_point_act = (
                                point if record.include_prior_point_act else 0) + prior_point_act

                            total_prior_point_act = partner.current_point_act
                            current_point_act = point + total_prior_point_act

                            vals_partner.update({
                                'mobile': mobile,
                                'current_point_act': current_point_act or 0.0,
                                'total_point_act': total_point_act or 0.0,
                            })
                            if date:
                                vals_partner.update({
                                    'birthday': date or False,
                                })
                            partner.write(vals_partner)
#                             print('Write Partner: ' + str(count) + str(mobile))
                    except Exception as e:
                        error = 'error'
                        note += str(e)
                    record.import_line_ids.create({
                        'error': error,
                        'note': note,
                        'partner_id': partner.id,
                        'mobile': mobile,
                        'prior_point_act': prior_point_act,
                        'exchange_point': point,
                        'point_up': point if point > 0 else 0,
                        'point_down': point if point < 0 else 0,
                        'current_point_act': total_point_act,
                        'import_id': record.id,
                        'prior_total_point_act': total_prior_point_act,
                        'current_total_point_act': current_point_act,
                        'more_info': more_info,
                        'bill_date': fields.Datetime.now(),
                    })
                    count += 1
            record.write({'state': 'done', 'date_done': fields.Datetime.now()})
        return True

    @api.model
    def auto_import_partner_point_history(self, log=False):
        #         date = time.strftime(DATETIME_FORMAT)
        #         date = self.env['res.users']._convert_user_datetime(date)
        #         if date.hour >= 6:
        #             return
        import_to_process = self.search(
            [('state', '=', 'validated')], order="id", limit=1)
        if import_to_process:
            try:
                import_to_process.action_import_done()
            except Exception as e:
                if log:
                    log(ustr(e))


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    @api.depends('categ_ids')
    def _get_categories_dom(self):
        for line in self:
            if line.categ_ids:
                categ_list = self.env['product.category']
                for item in line.categ_ids:
                    child_categ_ids = self.env['product.category'].search([
                        ('id', 'child_of', item.id)])
                    categ_list |= child_categ_ids
                domain = "[%s]" % (
                    ','.join(map(str, [i.id for i in categ_list])))
                line.categories_dom = domain
            else:
                line.categories_dom = False

    sale_type_ids = fields.Many2many(
        'pos.sale.type', 'loyalty_program_pos_sale_type_rel', 'lp_id', 'pst_id', string='Sale Types')
    categ_ids = fields.Many2many(
        'product.category', 'loyalty_program_product_category_rel', 'lp_id', 'pc_id', string='Categories')
    categories_dom = fields.Char(compute="_get_categories_dom", store=True)
    multiply_point_loyalty = fields.Float(default=0.0)

    @api.model
    def default_get(self, fields):
        rec = super(LoyaltyProgram, self).default_get(fields)
        rec.update({
            'rounding_method': 'down'
        })
        return rec


class LoyaltyLevel(models.Model):
    _inherit = 'loyalty.level'

    minimum_point = fields.Float('Minimum Point', copy=False)
    effective_time = fields.Integer('Effective time', copy=False)
    downgrade_method = fields.Selection(
        [('down', 'Downgrade'), ('close', 'Close')], default=False, required=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        if vals.get('customer', False):
            loyalty_level_id = self.env['loyalty.level'].search(
                [('from_point_act', '=', 0)], limit=1)
            if loyalty_level_id and loyalty_level_id.effective_time:
                today = self.env['res.users']._convert_user_datetime(
                    datetime.utcnow().strftime(DATETIME_FORMAT))
                vals['change_date_level'] = today.date()
                vals['date_get_loyalty_card'] = today.date()
                vals['expired_date'] = today.date(
                ) + relativedelta(months=loyalty_level_id.effective_time)
        return super(ResPartner, self).create(vals)
