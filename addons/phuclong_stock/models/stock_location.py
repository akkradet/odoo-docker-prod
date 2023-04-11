# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError

class Location(models.Model):
    _inherit = "stock.location"
    
    def name_get(self):
        ret_list = []
        for location in self:
            orig_location = location
            name = location.name
            if self._context.get('only_barcode_name') and location.barcode:
                name = location.barcode
            elif self._context.get('barcode_name') and location.barcode:
                name = (_('%s / %s')%(location.barcode, name))
            else:
                while location.location_id and location.usage != 'view':
                    location = location.location_id
                    if not name:
                        raise UserError(_('You have to set a name for this location.'))
                    name = (_('%s / %s')%(location.name, name))
            ret_list.append((orig_location.id, name))
        return ret_list
    
