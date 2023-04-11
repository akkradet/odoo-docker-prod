# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _

FORMAT = {}


class PartnerXlsx(models.AbstractModel):
    _name = 'report.phuclong_purchase.purchase_details_xlsx'
    _inherit = 'report.odoo_report_xlsx.abstract'

    # Định dạng page
    def page_setup(self, sheet):
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.set_footer('&LNgày in &D &RTrang &P/&N')
        sheet.set_row(0, 45.6)
        sheet.set_row(4, 45.6)

    # Định dạng format
    def make_format(self, workbook):
        header_title = workbook.add_format({'font_size': 16,
                                            'bold': True,
                                            #'fg_color': '#b7e1cd',
                                            })
        header_title.set_align('center')
        header_title.set_align('bottom')
        header_title.set_font_name('Times New Roman')
        line_italic = workbook.add_format({'font_size': 10,
                                           'italic': True,
                                           'bold': True,
                                           })
        line_italic.set_font_name('Times New Roman')
        line_italic.set_align('center')
        line_italic.set_align('vcenter')
        table_bold = workbook.add_format({'font_size': 12,
                                          'align': 'vcenter',
                                          'bold': True,
                                          'fg_color': '#dddddd',
                                          })
        table_bold.set_border()
        table_bold.set_font_name('Times New Roman')
        table_bold.set_text_wrap()
        table_bold.set_align('center')
        table_content = workbook.add_format(
                           {'font_size': 10, 'align': 'vcenter', })
        table_content.set_border()
        table_content.set_text_wrap()
        table_content.set_align('center')
        table_number = workbook.add_format({'font_size': 10,
                                            'align': 'vcenter', })
        table_number.set_border()
        table_number.set_align('right')
#         table_number.set_num_format('#,##0.00')

        FORMAT.update({'header_title': header_title,
                       'line_italic': line_italic,
                       'table_bold': table_bold,
                       'table_content': table_content,
                       'table_number': table_number
                       })

    def generate_header(self, sheet, rcs):
        if rcs.type_report == 'purchase':
            report_name = 'Báo cáo tổng hợp đặt hàng theo ngày'
        else:
            report_name = 'Báo cáo tổng hợp trả hàng theo ngày'
        sheet.merge_range('A1:F1', report_name,
                          FORMAT.get('header_title'))
        sheet.write(1, 2, 'Ngày in', FORMAT.get('line_italic'))
        sheet.write(1, 3, rcs.get_current_date(), FORMAT.get('line_italic'))
        sheet.write(2, 2, 'Ngày', FORMAT.get('line_italic'))
        sheet.write(2, 3, rcs.get_date_from() + ' - ' + rcs.get_date_to(),
                    FORMAT.get('line_italic'))
        return 3

    def general_data(self, sheet, rcs, rowpos):
        sheet.write(rowpos, 0, 'Mã sản phẩm', FORMAT.get('table_bold'))
        sheet.write(rowpos, 1, 'Tên sản phẩm', FORMAT.get('table_bold'))
        sheet.write(rowpos, 2, 'Mã tham chiếu', FORMAT.get('table_bold'))
        sheet.write(rowpos, 3, 'Đơn vị tính', FORMAT.get('table_bold'))
        for r in range(4):
            sheet.set_column(rowpos, r, 21)
        col = 4
        get_products, warehouse_ids = rcs.get_data_products()
        for warehouse in warehouse_ids:
            sheet.write(rowpos, col, warehouse.code + ' - ' + warehouse.name, FORMAT.get('table_bold'))
            sheet.set_column(rowpos, col, 24)
            col += 1
        sheet.write(rowpos, col, 'Tổng cộng', FORMAT.get('table_bold'))
        sheet.set_column(rowpos, col, 21)
        rowpos += 1
        for product in get_products:
            sheet.write(rowpos, 0, product.default_code or '', FORMAT.get('table_content'))
            sheet.write(rowpos, 1, product.name, FORMAT.get('table_content'))
            sheet.write(rowpos, 2, product.ref_code or '', FORMAT.get('table_content'))
            sheet.write(rowpos, 3, product.uom_id and product.uom_id.name or '', FORMAT.get('table_content'))
            col_ware = 4
            total = 0.0
            for warehouse in warehouse_ids:
                total_product_qty = rcs.total_purchased_product_qty(product, warehouse)
                if total_product_qty < 0:
                    total_product_qty = 0
                sheet.write(rowpos, col_ware, total_product_qty, FORMAT.get('table_number'))
                total += total_product_qty
                col_ware += 1
            sheet.write(rowpos, col_ware, total, FORMAT.get('table_number'))
            rowpos += 1

    def generate_xlsx_report(self, workbook, data, partners):
        self.make_format(workbook)
        for rcs in partners:
            if rcs.type_report == 'purchase':
                report_name = 'Mua hàng hằng ngày'
            else:
                report_name = 'Trả hàng hằng ngày'
            sheet = workbook.add_worksheet(report_name)
            self.page_setup(sheet)
            rowpos = self.generate_header(sheet, rcs)
            rowpos = self.general_data(sheet, rcs, rowpos + 1)

