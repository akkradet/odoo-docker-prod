# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class ReportCustomer(models.TransientModel):
    _inherit = 'report.customer'

    type = fields.Selection(selection_add=[('new_customers', 'New Customers'), ('coming_downgrade', 'Coming Downgrade Soon')])

    def get_customers_loyalty(self):
        if self.type == 'coming_downgrade':
            sql ='''
                SELECT rp.id, rp.name,
                card.appear_code,
                rp.mobile,
                to_char(rp.birthday, 'DD-MM-YYYY') birthday,
                case when rp.gender = 'male' then 'Nam' when rp.gender = 'female' then 'Nữ' else '' end gender,
                rp.email,
                rp.street,
                rw.name ward_name,
                rd.name district_name,
                rcs.name state_name,
                CASE
                    WHEN rp.current_point_act is NULL THEN (SELECT ll.level_name FROM loyalty_level ll 
                                                            where ll.from_point_act <= 0.0
                                                            AND ll.to_point_act >= 0.0
                                                            AND ll.active = true LIMIT 1)
                    ELSE ll.level_name
                END,
                rp.current_point_act::int point,
                to_char(rp.date_get_loyalty_card, 'DD-MM-YYYY') date_get_loyalty_card,
                to_char(rp.expired_date, 'DD-MM-YYYY') expired_date
                FROM res_partner rp join loyalty_level ll on rp.current_point_act between ll.from_point_act and ll.to_point_act 
                LEFT JOIN cardcode_info card ON card.id = rp.appear_code_id
                LEFT JOIN res_ward rw on rp.ward_id = rw.id
                LEFT JOIN res_district rd on rp.district_id = rd.id
                LEFT JOIN res_country_state rcs on rp.state_id = rcs.id                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
                WHERE customer is true 
                and rp.expired_date between '%s' and '%s' AND ll.active is true and rp.current_point_act < ll.minimum_point
                order by name
            '''%(self.date_start, self.date_end)
        else:
            query = ''' AND rp.date_get_loyalty_card BETWEEN '%s' AND '%s'
            ''' % (self.date_start, self.date_end)
            sql = '''
                SELECT rp.id, rp.name,
                card.appear_code,
                rp.mobile,
                to_char(rp.birthday, 'DD-MM-YYYY') birthday,
                case when rp.gender = 'male' then 'Nam' when rp.gender = 'female' then 'Nữ' else '' end gender,
                rp.email,
                rp.street,
                rw.name ward_name,
                rd.name district_name,
                rcs.name state_name,
                CASE
                    WHEN rp.current_point_act is NULL THEN (SELECT ll.level_name FROM loyalty_level ll 
                                                            where ll.from_point_act <= 0.0
                                                            AND ll.to_point_act >= 0.0
                                                            AND ll.active = true LIMIT 1)
                    ELSE ll.level_name
                END,
                rp.current_point_act::int point,
                to_char(rp.date_get_loyalty_card, 'DD-MM-YYYY') date_get_loyalty_card,
                to_char(rp.expired_date, 'DD-MM-YYYY') expired_date
                FROM res_partner rp
                LEFT JOIN loyalty_level ll on ll.from_point_act <= rp.current_point_act 
                                            AND ll.to_point_act >= rp.current_point_act 
                                            AND ll.active = TRUE
                LEFT JOIN cardcode_info card ON card.id = rp.appear_code_id
                LEFT JOIN res_ward rw on rp.ward_id = rw.id
                LEFT JOIN res_district rd on rp.district_id = rd.id
                LEFT JOIN res_country_state rcs on rp.state_id = rcs.id
                WHERE rp.customer IS true
                %s
                ORDER BY rp.name
            ''' % (query)
        self._cr.execute(sql)
        return self._cr.dictfetchall()

    def get_gender(self, gender):
        if gender:
            value_gender = dict(self.env['res.partner'].fields_get(['gender'])['gender']['selection'])
            gender = value_gender[gender]
        return gender

    def get_display_address(self, partner_id, type):
        partner_id = self.env['res.partner'].sudo().browse(partner_id)
        if type == 1:
            return partner_id.street or ''
        elif type == 2:
            return partner_id.ward_id and partner_id.ward_id.name or ''
        elif type == 3:
            return partner_id.district_id and partner_id.district_id.name or ''
        else:
            return partner_id.state_id and partner_id.state_id.name or ''
    
    def get_report_name(self):
        report_name = u'BẢNG BÁO CÁO THÔNG TIN KHÁCH HÀNG'
        if self.type == 'new_customers':
            report_name += u' MỚI'
        return report_name
        
    
    