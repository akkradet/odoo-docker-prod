from odoo import fields, models, api
default_pub_key = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCODwVTIdiolVjA+4hlXzUpFaI4' +\
                  'WQKgVvSxTcyo97HYUWHAvduIPWmThMNm6yKnr6BCNItV921SvtR1APYjYxd+5kL6' +\
                  'TDgteu8fov1VtIVJT7kXLiNp0MQ5xZhtpSnM+zNtO2j3qxzx9qPF7Mi2yns8TUwh' +\
                  'wyuc8aHTObNI/1cxEwIDAQAB'
                  
default_sec_key = 'MIICXAIBAAKBgQCODwVTIdiolVjA+4hlXzUpFaI4WQKgVvSxTcyo97HYUWHAvduI' +\
                  'PWmThMNm6yKnr6BCNItV921SvtR1APYjYxd+5kL6TDgteu8fov1VtIVJT7kXLiNp' +\
                  '0MQ5xZhtpSnM+zNtO2j3qxzx9qPF7Mi2yns8TUwhwyuc8aHTObNI/1cxEwIDAQAB' +\
                  'AoGAKtje+0cPKTH6liKH7kN8LksnJaW7RA9WOJBFtYUYMC3DtTXOnFYhnOwDX+x2' +\
                  'BGvVg4KDsEczwyxpumyy0NOXhyjYTPlAeZN9DbLuimnit8KQpoDcqFMTQkjNo1eZ' +\
                  'E+s0ZFX/eaRGnRnQVanvmC3N4C2CHH3NlOKdCmaJNXEYG6kCQQD48f/sMsfXl1xj' +\
                  '/o2cI5PtxdjW9p+5IMlH6G3KHUrOZNX70hD/C0eO2NRumuhFmsXQFYSV5cMI1Izs' +\
                  'DNGJ5PTlAkEAkhWZwR7221JBkbJKDUFSrikoOgvdqiGW2cTtGYgKTEysblTlJayo' +\
                  'KM6W2/CgEnEwa34nlYAlq2PGzrKnWOHmlwJARkIGOGMcg3v0V0RAMxDXbwOnbwOr' +\
                  'kFPwepreYWxi8F0FB00B/vjv+SC4035kj0BfE5r/EE8H/DYAj54OhRxZAQJAJ9wQ' +\
                  '+erS/IDzNyfooLlEMBU2zq/SKcvEd2MONrsx5CO/oNM1OxRjRc8oxpZfdui/h3UC' +\
                  'o/41SRCOfHOuycfJvQJBAOuH0tWKptuwTVFLpjQejLr8JYcgyAxiZEH6dTlayH3e' +\
                  '/gAEcMcPbMFgC+ZqxVaVLWrzma9eHGR2RHaY6RQGtSU='

class APIGiftCode(models.Model):
    _name = "giftcode.api.config"

    name = fields.Char('Name', required=True)
    type = fields.Selection([
        ('urbox', 'Urbox'),
        ('giftpop', 'Gift Pop'),
        ], string="Type", default=False)
    api_url = fields.Char('API URL', required=True)
    access_key = fields.Char('Access key', required=True)
    branch_code = fields.Char()
    agent_site = fields.Integer('Agent site', required=True)
    brand_id = fields.Integer('Brand', required=False)
    methods = fields.One2many(
        'giftcode.api.config.method',
        'api_config_id',
        string='Types')
    store_ids = fields.One2many('giftcode.api.store', 'store_conf_id', string='Store Setting')
    store_mapping_type = fields.Selection([('all2one', 'All store Odoo - One store Giftcode'), ('one2one', 'One store Odoo - One store Giftcode')], 
                                          string='Store Mapping Type', required=True, default='all2one')
    pub_key = fields.Text('Public Key', required=True, default=default_pub_key)
    sec_key = fields.Text('Secret Key', required=True, default=default_sec_key)
    
    @api.onchange('store_mapping_type')
    def onchange_store_mapping_type(self):
        if self.store_mapping_type == 'one2one':
            store_config = self.env['giftcode.api.store'].sudo()
            available_store_conf = self.store_ids
            new_store_conf = []
            store_not_conf = self.env['stock.warehouse'].sudo().search([('id', 'not in', [x.store_id.id for x in available_store_conf])]) or []
            for store in store_not_conf:
                new_conf_id = store_config.create({'store_id':store.id})
                new_store_conf.append((4, new_conf_id.id))
    
            if len(new_store_conf):
                self.write({'store_ids': new_store_conf})

class APIGiftCodeLine(models.Model):
    _name = "giftcode.api.config.method"

    type = fields.Selection([
        ('activate', 'Activate'),
        ('validate', 'Check')
        ], string="Type", required=True, default="validate")
    api_url = fields.Char('API URL', required=True)
    api_config_id = fields.Many2one('giftcode.api.config')
    
class APIGiftCodeStore(models.Model):
    _name = "giftcode.api.store"
    _order = "store_code"
    
    store_conf_id = fields.Many2one('giftcode.api.config', string="Config", ondelete='cascade')
    store_code = fields.Char(related="store_id.code", string="Store Code", required=True)
    store_id = fields.Many2one('stock.warehouse', string="Store", required=True)
    gifcode_store_id = fields.Char('Giftcode Store ID', size=64, required=False)
    
    
class GiftcodeApiResponse(models.Model):
    _name = 'giftcode.api.response'
    _order = 'create_date desc'
    
    giftcode_type = fields.Selection([
        ('urbox', 'Urbox'),
        ('giftpop', 'Gift Pop'),
        ], string="Giftcode Type")
    type = fields.Selection([
        ('activate', 'Activate'),
        ('validate', 'Check')
        ], string="API Type")
    order_name = fields.Char()
    request_string = fields.Char()
    response_string = fields.Char('Response String')
