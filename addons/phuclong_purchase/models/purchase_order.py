# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import json
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import format_datetime

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def default_get(self, fields):
        rec = super(PurchaseOrder, self).default_get(fields)
        partner_id = self.env['res.partner'].search([('is_default_vendor', '=', True),
                                                     ('supplier', '=', True)], limit=1)
        if partner_id:
            rec.update({
                'partner_id': partner_id.id,
            })
        return rec

    def _is_orderpoint(self):
        for rcs in self:
            is_orderpoint = False
            for line in rcs.order_line.filtered(lambda x: x.orderpoint_id != False):
                if line.product_id == line.orderpoint_id.product_id:
                    is_orderpoint = True
                    continue
            rcs.is_orderpoint = is_orderpoint
            
    def _is_product_max_qty_exceeded(self):
        for rcs in self:
            is_product_max_qty_exceeded = False
            if any(rcs.order_line.filtered(lambda x: x.is_product_max_qty_exceeded != False)):
                is_product_max_qty_exceeded = True
            rcs.is_product_max_qty_exceeded = is_product_max_qty_exceeded

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    date_planned = fields.Datetime(string='Receipt Date', index=True, tracking=True)
    return_reason_id = fields.Many2one('reason.config', string='Return Reason')
    confirm_person_id = fields.Many2one('res.users', 'Confirm Person', tracking=True, readonly=True)
    approved_person_id = fields.Many2one('res.users', 'Approved Person', tracking=True, readonly=True)
    print_no_price = fields.Boolean(string="Have no price", default=False)
    is_orderpoint = fields.Boolean(string='Is Orderpoint', compute="_is_orderpoint")
    is_no_approval_required = fields.Boolean(string='No Approval Required', readonly=True, default=False)
    purchase_type_id = fields.Many2one('purchase.type.config', 'Purchase Type')
    vendor_document = fields.Char()
    
    is_product_max_qty_exceeded = fields.Boolean(compute="_is_product_max_qty_exceeded")
    is_reordered_po = fields.Boolean(
        string='Is Reordered PO',
        readonly=True,
        default=False
    )
    picking_date_done = fields.Datetime(string='Date of transfer')
    
    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    # _onchange_partner_id, _onchange_product_id
    @api.onchange('type', 'order_line',
                  'order_line.product_qty')
    def onchange_type_product_qty(self):
        for rcs in self:
            print ('1 ', rcs.order_line)
            if rcs.order_line:
                order_line_negative = rcs.order_line.filtered(lambda x: x.product_qty < 0)
                order_line_positive = rcs.order_line.filtered(lambda x: x.product_qty > 0)
                # so duong
                if order_line_negative and order_line_positive and rcs.type == 'purchase':
                    if rcs.order_line[0] in order_line_positive or rcs.name != 'new':
                        raise UserError(_("The current number on the PO is a positive number, "
                                          "you are not allowed to enter a negative number."
                                          "If you want to enter a negative number, please create another PO"))
                if order_line_positive and order_line_negative and rcs.type == 'return':
                    # So am
                    if rcs.order_line[0] in order_line_negative or rcs.name != 'new':
                        raise UserError(_("The current number on the PO is a negative number, "
                                          "you are not allowed to enter a positive number. "
                                          "If you want to enter a negative number, please create another PO"))

                if rcs.order_line[0] in order_line_negative:
                    rcs.type = 'return'
                else:
                    rcs.type = 'purchase'
                for line in rcs.order_line:
                    order_line_orderpoint = rcs.order_line.filtered(lambda x: x.product_id == line.product_id \
                                                                    and x.orderpoint_id and x.id != line.id)
                    if order_line_orderpoint:
                        raise UserError(_("This product already in the purchase order, please check again!"))

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    # action_draft, action_done, action_invoice_create, action_invoice_view
    def action_purchase_stock_scheduler(self):
        action = self.env.ref('phuclong_purchase.action_wizard_purchase_stock_scheduler_compute')
        result = action.read()[0]
        result['context'] = {'default_purchase_id': self.id,
                             }
        access = self.env['ir.model.access']
        if access.check_groups("purchase.group_purchase_user") and access.check_groups("purchase.group_purchase_manager"):
            result['context'].update({'default_is_warning': True})
        return result

    def action_print_no_price(self):
        for rcs in self:
            if rcs.print_no_price:
                rcs.print_no_price = False
            else:
                rcs.print_no_price = True

    def print_report_quotation(self):
        return self.env.ref(
            'phuclong_purchase.report_purchase_order_py3o').report_action(self)

    def print_report_price_quotation(self):
        self.print_no_price = True
        return self.env.ref('purchase.action_report_purchase_order').report_action(self)

    def button_cancel(self):
        for order in self:
            if any(order.picking_ids.filtered(lambda x: x.state not in ('cancel','draft'))):
                raise UserError(_('Stock picking is being processed. To cancel purchase order, you must be cancel stock picking related'))
            if any(order.invoice_ids.filtered(lambda x: x.state != 'cancel')):
                raise UserError(_('Vendor bill is being processed. To cancel purchase order, you must be cancel vendor bill related'))
        return super(PurchaseOrder, self).button_cancel()

    def button_refuse(self):
        for rcs in self:
            rcs.button_cancel()

    def button_approve(self, force=False):
        access = self.env['ir.model.access']
        for order in self:
            if not access.check_groups("purchase.group_purchase_manager") and not order.is_no_approval_required:
                raise UserError(_("You're not able to Approve an Purchase Order. \nPlease contact Administrator."))
            order.approved_person_id = self._uid
        return super(PurchaseOrder, self).button_approve()

    def button_confirm(self):
        """
        Điều chỉnh theo project Phúc Long
        """
        for order in self:
            if not order.date_planned:
                raise UserError(_("The field 'Receipt Date' is required, please complete it to validate "
                                  "the Purchase Orther"))
            if order.date_planned < order.date_order:
                raise UserError(_("Receipt date must be large than Order date"))
                
            order.confirm_person_id = self._uid

            #ham besco_purchase
            if order.state not in ['draft', 'sent']:
                return self.refresh()
            lines = order.mapped('order_line')
            
            if any(lines.filtered(lambda l: l.product_qty == 0)):
                # theo task T08268
                lines_to_unlink = lines.filtered(lambda l: l.product_qty == 0)
                lines_to_unlink.unlink()
            
            if not order.mapped('order_line'):
                raise UserError(_('Unable to confirm order as lines do not define.'))
            elif self.env['ir.config_parameter'].sudo().get_param('base.group_multi_currency') and order.company_currency_id != order.currency_id and order.currency_rate <= 1:
                raise UserError(_('Please enter currency conversion rates.'))
            
#                 raise UserError(_('Ordered quantity/ price unit of product must be greater than 0.'))
#             elif any(lines.filtered(lambda l: l.product_qty == 0 or l.price_unit == 0)):
#                 raise UserError(_('Ordered quantity/ price unit of product must be greater than 0.'))
            if order.total_qty < 0 and 'R' != self.name[0]:
                order.name = 'R' + _(order.name)

            #ham odoo 13
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.company.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager')\
                    or order.is_no_approval_required:
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True
        #return super(PurchaseOrder, self).button_confirm()

    def _create_picking_return(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if order.type != 'return':
                continue
            pickings = order.picking_ids.filtered(lambda x: x.state not in ('done','cancel') and x.picking_type_id.code =='return_supplier')
            if not pickings:
                res = order._prepare_picking()
                picking = StockPicking.create(res)
                picking.message_post_with_view('mail.message_origin_link', values={'self': picking, 'origin': order}, subtype_id=self.env.ref('mail.mt_note').id)
            else:
                picking = pickings[0]
            moves = order.order_line.filtered(lambda x: x.product_qty < 0)._create_stock_moves(picking)
            moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
            moves._action_assign()
        return True

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if order.type != 'purchase':
                continue
#             order.type = 'purchase'
            pickings = order.picking_ids.filtered(lambda x: x.state not in ('done','cancel') and x.picking_type_id.code =='incoming')
            if not pickings:
                res = order._prepare_picking()
                picking = StockPicking.create(res)
                picking.message_post_with_view('mail.message_origin_link', values={'self': picking, 'origin': order}, subtype_id=self.env.ref('mail.mt_note').id)
            else:
                picking = pickings[0]
            moves = order.order_line.filtered(lambda x: x.product_qty > 0)._create_stock_moves(picking)
            moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
            moves._action_assign()
        return True

    @api.constrains('type', 'order_line', 'order_line.product_qty')
    def _check_type_order_line_qty(self):
        for rcs in self:
            order_line_negative = rcs.order_line.filtered(lambda x: x.product_qty < 0)
            order_line_positive = rcs.order_line.filtered(lambda x: x.product_qty > 0)
            # so duong
            if order_line_negative and order_line_positive and rcs.type == 'purchase':
                if rcs.order_line[0] in order_line_positive or rcs.name != 'new':
                    raise UserError(_("The current number on the PO is a positive number, "
                                      "you are not allowed to enter a negative number."
                                      "If you want to enter a negative number, please create another PO"))
            elif order_line_positive and order_line_negative and rcs.type == 'return':
                # So am
                if rcs.order_line[0] in order_line_negative or rcs.name != 'new':
                    raise UserError(_("The current number on the PO is a negative number, "
                                      "you are not allowed to enter a positive number. "
                                      "If you want to enter a negative number, please create another PO"))
            if rcs.type == 'return' and order_line_positive:
                #so am
                raise UserError(_("You cann't purchase items on the Return Purchase Order"))

            if rcs.type == 'purchase' and order_line_negative:
                #so duong
                raise UserError(_("You cann't purchase items on the Purchase Order"))

    @api.onchange('order_line')
    def _check_duplicate_product(self):
        product_ids = []
        for line in self.order_line:
            if line.product_id:
                if line.product_id.id in product_ids:
                    raise ValidationError(_("This product is already in the purchase order, please check again!"))
                else:
                    product_ids.append(line.product_id.id)
    

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        for order in self:
            if order.state not in ['cancel' , 'draft']:
                raise UserError(_('In order to delete a purchase order, you must cancel it first.'))
        return super(models.Model, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('type', False) == 'return':
            vals.update({'name': self.env['ir.sequence'].next_by_code('purchase_return_order_rollback') or False})
        domain_seq = []
        domain_seq.append(('code', '=', 'purchase.order'))
        if 'company_id' not in vals:
            vals.update({'company_id': self.env.user.company_id.id})
        if vals.get('company_id',False):
            domain_seq.append('|')
            domain_seq.append(('company_id', '=', False))
            domain_seq.append(('company_id', '=', vals['company_id']))
        exist_seq = self.env['ir.sequence'].search(domain_seq, limit=1)
        if not exist_seq:
            raise UserError(_("Sequence of Purchase Order is not defined."))
        company_analytic_account_id = vals.get('company_analytic_account_id',False)
        if vals.get('warehouse_id', False) and not vals.get('company_analytic_account_id',False):
            warehouse = self.env['stock.warehouse'].browse(vals['warehouse_id'])
            company_analytic_account_id = warehouse.company_account_analytic_id.id
        if not vals.get('name', False):
            vals['name'] = exist_seq.with_context(transaction_company_id=vals['company_id'],\
                                            company_analytic_account_id=company_analytic_account_id).next_by_id()

        res = super(models.Model, self).create(vals)
        if vals.get('date_planned', False):
            res.message_post_date_planned(vals.get('date_planned'))
        return res

    def message_post_date_planned(self, date_planned):
        self.ensure_one()
        if isinstance(date_planned, datetime):
            date_planned = fields.Datetime.to_string(date_planned)
        self.message_post(body=_("Receipt Date: %s") % format_datetime(self.with_context(use_babel=True).env, date_planned, tz=self.env.user.tz or 'Asia/Ho_Chi_Minh', lang_code=self.env.user.lang or 'vi_VN'))

    # def write(self, vals):
    #     res = super(PurchaseOrder, self).write(vals)
    #     for rcs in self:
    #         if not rcs.date_planned and vals.get('date_planned', False):
    #             rcs.message_post_date_planned(vals.get('date_planned'))
    #     return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        ret_val = super(PurchaseOrder, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        doc = etree.XML(ret_val['arch'])
        if view_type == 'form':
            access = self.env['ir.model.access']
            if access.check_groups("purchase.group_purchase_user") and access.check_groups("purchase.group_purchase_manager"):
                for node in doc.xpath("//button[@name='button_refuse']"):
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['invisible'] = True
                    node.set("modifiers", json.dumps(modifiers))
            invisibile_button = ['action_rfq_send', 'print_quotation']
            for field in invisibile_button:
                for node in doc.xpath("//button[@name='%s']" % field):
                    modifiers = json.loads(node.get("modifiers"))
                    modifiers['invisible'] = True
                    node.set("modifiers", json.dumps(modifiers))
        ret_val['arch'] = etree.tostring(doc, encoding='unicode')
        return ret_val

    def get_vietname_datetime(self, date):
        if date:
            date = self.env['res.users']._convert_user_datetime(date)
            return date.strftime('%d/%m/%Y %H:%M:%S')
