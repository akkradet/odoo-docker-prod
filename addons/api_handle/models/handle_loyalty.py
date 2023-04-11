from odoo import fields, models, api
from datetime import datetime, date
from odoo.addons.phuclong_restful_api.common import invalid_response, valid_response
import json

class handleLoyaltyResponse(models.Model):
    _inherit = 'loyalty.program'

    def load_active_reward(self):
        exp_date = date.today()
        exp_date_valid = self.search([('from_date', '<', exp_date), ('to_date', '>=', exp_date)])

        if exp_date_valid:
            dict_program = []

            for item_program in exp_date_valid:
                program_info = {
                    'id': item_program.id,
                    'name': item_program.name,
                    'reward_ids': [],
                }

                for item_reward in item_program.reward_ids:
                    gift_product_ids = []
                    if item_reward.gift_product_ids:
                        for item_product in item_reward.gift_product_ids:
                            gift_product_ids.append(item_product.id)

                    reward_info = {
                        'id': item_reward.id,
                        'name': item_reward.name,
                        'type': item_reward.type,
                        'gift_product_id': item_reward.gift_product_id.id or None,
                        'category_id': item_reward.category_id.id or None,
                        'gift_product_ids': gift_product_ids or None,
                        'point_cost': item_reward.point_cost,
                    }
                    program_info['reward_ids'].append(reward_info)

                dict_program.append(program_info)

            return valid_response(dict_program)
        else:
            return invalid_response('loyalty program', 'All of loyalty program is out of expiry date', 402)