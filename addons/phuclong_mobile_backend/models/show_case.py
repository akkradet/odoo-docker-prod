from odoo import models, api, _, fields, tools
from datetime import datetime, date
import lxml
import re
image_re = re.compile(r"data:(image/[A-Za-z]+);base64,(.*)")

class ShowCase(models.Model):
    _name = 'show.case'

    name = fields.Char(string="Title")
    short_des = fields.Text(string="Short Description")
    view_type = fields.Selection([('1', 'News'), ('2', 'Promotion')], string="View Type")
    # action = fields.Selection([('product', 'Product'), ('news', 'News')], string="Action")
    product_id = fields.Many2one('product.template', string="Product")
    body_arch = fields.Html(string='Body', translate=False)
    body_html = fields.Html(string='Body converted to be send by mail', sanitize_attributes=False)
    image = fields.Image(string="Image")
    active = fields.Boolean(default=True)
    is_published = fields.Boolean(default=False)
    use_for = fields.Selection([('product', 'Product'), ('combo', 'Combo')])
    combo_id = fields.Many2one('sale.promo.combo', string="Combo")

    @api.model
    def create(self, values):
        if values.get('body_html'):
            values['body_html'] = self.with_context(show_case=True)._convert_inline_images_to_urls(values['body_html'])
        return super(ShowCase, self).create(values)

    def write(self, values):
        if values.get('body_html'):
            values['body_html'] = self.with_context(show_case=True)._convert_inline_images_to_urls(values['body_html'])
        return super(ShowCase, self).write(values)

    def action_published(self):
        if self.is_published:
            self.is_published = False
        else:
            self.is_published = True

    def _convert_inline_images_to_urls(self, body_html):
        """
        Find inline base64 encoded images, make an attachement out of
        them and replace the inline image with an url to the attachement.
        """

        def _image_to_url(b64image: bytes):
            """Store an image in an attachement and returns an url"""
            attachment = self.env['ir.attachment'].create({
                'datas': b64image,
                'name': "cropped_image_mailing_{}".format(self.id),
                'type': 'binary',})

            attachment.generate_access_token()
            if self._context.get('show_case'):
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                return base_url + '/web/image/%s?access_token=%s' % (
                    attachment.id, attachment.access_token)
            return '/web/image/%s?access_token=%s' % (
                attachment.id, attachment.access_token)

        modified = False
        root = lxml.html.fromstring(body_html)
        for node in root.iter('img'):
            match = image_re.match(node.attrib.get('src', ''))
            if match:
                mime = match.group(1)  # unsed
                image = match.group(2).encode()  # base64 image as bytes

                node.attrib['src'] = _image_to_url(image)
                modified = True
            elif node.attrib.get('src', ''):
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                node.attrib['src'] = base_url + node.attrib['src']
                modified = True
        if modified:
            return lxml.html.tostring(root)

        return body_html