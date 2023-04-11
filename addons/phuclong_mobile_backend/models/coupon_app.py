from odoo import models, fields, api, _
from dateutil import relativedelta


class CouponAPP(models.Model):
    _name = 'coupon.app'
    _order = 'publish_date DESC, create_date DESC'

    def backpoint_partner(self):
        for rec in self:
            if rec.partner_id:
                partner_id = rec.partner_id
                total_point_act = partner_id.total_point_act
                count_discount_birth = partner_id.count_discount_birth
                year_discount_birth = partner_id.year_discount_birth
                is_update = False
                if rec.type == 'birthday' and rec.publish_date and rec.publish_date.year == year_discount_birth:
                    count_discount_birth -= 1
                    is_update = True
                if rec.type == 'point':
                    total_point_act += rec.point_cost
                    is_update = True
                if is_update:
                    partner_id.write({
                        'total_point_act': total_point_act,
                        'count_discount_birth': max(count_discount_birth, 0)
                    })

    def unlink(self):
        # Add code here
        self.backpoint_partner()
        return super(CouponAPP, self).unlink()

    name = fields.Char('Code', required=True)
    size = fields.Integer(string='Size Code',
                          compute='_compute_size', store=True)

    @api.depends('name')
    def _compute_size(self):
        for rec in self:
            rec.size = len(rec.name)

    type = fields.Selection(
        [('birthday', 'Birthday'), ('point', 'Point')], 'Type')
    gift_type = fields.Selection(
        [('product', 'Product'), ('discount', 'Discount')], 'Gift Type')
    publish_date = fields.Date('Publish Date')
    effective_date_from = fields.Date('Effective Date From')
    effective_date_to = fields.Date(
        'Effective Date To', store=True)
    loyalty_level_id = fields.Many2one(
        comodel_name='loyalty.level', string='Loyalty Level')
    loyalty_reward_id = fields.Many2one(
        comodel_name='loyalty.reward', string='Loyalty Reward')
    image = fields.Char(string='Image', compute='_compute_image', store=True)
    point_cost = fields.Float(string='Point Cost', default=0.0)
    content = fields.Html(string='Content', default='')
    contact = fields.Html(string='Contact', default='')

    def cron_expire_coupon_app(self, log=False):
        try:
            today = fields.Date.context_today(self)
            coupon_app_ids = self.sudo().search([
                ('state', '=', 'new'),
                ('effective_date_to', '<', today),
                ('pos_order_id', '=', False)
            ])
            if coupon_app_ids:
                coupon_app_ids.action_expire()
        except Exception as e:
            if log:
                log(e)

    @api.depends('loyalty_reward_id', 'loyalty_level_id')
    def _compute_image(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        for rec in self:
            image = ''
            if rec.loyalty_reward_id:
                image = rec.loyalty_reward_id._prepair_url_image(base_url)
            elif rec.loyalty_level_id:
                image = rec.loyalty_level_id._prepair_url_image(base_url)
            rec.image = image

    state = fields.Selection([('new', 'New'), ('expire', 'Expire'),
                              ('used', 'Used'), ('cancel', 'Cancel')], 'Status', default='new')
    discount = fields.Float('Discount')
    product_ids = fields.Many2many(
        comodel_name='product.template', string='Product List')
    partner_id = fields.Many2one('res.partner')
    pos_order_line_ids = fields.One2many(
        comodel_name='pos.order.line', inverse_name='coupon_app_id', string='POS Order Lines', inverse=False)
    pos_order_id = fields.Many2one(
        comodel_name='pos.order', string='Order Reference', related='pos_order_line_ids.order_id', store=True, readonly=True, inverse=False)
    pos_order_ref = fields.Char(string='POS Reference')
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse', related='pos_order_id.warehouse_id', store=True, readonly=True)
    store_id = fields.Many2one(
        comodel_name='res.store', string='Store', readonly=True)
    date_used = fields.Datetime(
        string='Date Used', related='pos_order_id.date_order', store=True, readonly=True)
    order_in_app = fields.Boolean(
        'Order in App', related='pos_order_id.order_in_app', store=True, readonly=True)

    @api.constrains('pos_order_id')
    def _check_pos_order_id(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state == 'new' and rec.pos_order_id:
                rec.action_used()
                rec.pos_order_ref = rec.pos_order_id.pos_reference
            elif rec.state == 'used' and not rec.pos_order_id:
                rec.backpoint_partner()
                if rec.effective_date_to:
                    if rec.effective_date_to > today:
                        rec.action_expire()
                    else:
                        rec.action_new()

    @api.constrains('warehouse_id')
    def _check_warehouse_id(self):
        for rec in self:
            rec.store_id = rec.warehouse_id and self.env['res.store'].sudo().search(
                [('warehouse_id', '=', rec.warehouse_id.id)]) or False

    def action_new(self):
        self.write({
            'state': 'new'
        })

    def action_used(self):
        self.write({
            'state': 'used'
        })

    def action_expire(self):
        self.write({
            'state': 'expire'
        })
