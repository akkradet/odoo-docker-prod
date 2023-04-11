odoo.define('phuclong_pos_stock.form_renderer', function (require) {
    "use strict";
    
    var core = require('web.core');
    var data = require('web.data');
    var utils = require('web.utils');
    var FormView = require('web.FormView');
    var Widget = require('web.Widget');
    var session = require('web.session');
    var _t = core._t;
    var QWeb = core.qweb;
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;
    var FormRenderer = require('web.FormRenderer');
	var FormController = require('web.FormController');
    var rpc = require("web.rpc");
    
    FormRenderer.include({
        events: _.extend({}, FormRenderer.prototype.events, {
            "click .print-picking-receipt": "get_picking_info",
        }),
        get_picking_info: function(){
            var self = this;
            rpc.query({
                    model: 'stock.picking',
                    method: 'get_picking_info',
                    args: [this.state.data.id],
                })
                .then(function (result) {
                    var values = {
                        widget:self,
                        warehouse_name: self.state.data.warehouse_id.data.display_name,
                        location_from: result.location_from,
                        location_to: result.location_to,
                        date: moment().format('L LT'),
                        user: result.user,
                        picking_name: self.state.data.display_name,
                        lines: result.lines
                    }
                    var el_str = QWeb.render('PickingReceipt',values);
                    var div_html = $('div.PickingReceipt');
                    if(div_html.length == 0){
                        div_html = document.createElement("div");
                        div_html.classList.add('PickingReceipt');
                    }
                    $('body .o_action_manager').after(div_html);
                    $('div.PickingReceipt').html(el_str);
                    setTimeout(function(){}, 1000);
                    $('body .o_action_manager').addClass('o_hidden');
                    self.print_bill();
                    $('body .o_action_manager').removeClass('o_hidden');
                    $('div.PickingReceipt').empty();
                });
        },
        _renderPicking_Receipt: function (node){
            var $print_button = $('<button>')
                .text(node.children[0])
                .addClass('btn btn-binary print-picking-receipt')
                .css('background-color', '#00A09D')
                .css('color', '#fff');
            this._handleAttributes($print_button, node);
            this._registerModifiers(node, this.state, $print_button);
            return $print_button;
        },
//        _renderHeaderButtons: function (node) {
//            var self = this;
//            var $buttons = $('<div>', {class: 'o_statusbar_buttons'});
//            _.each(node.children, function (child) {
//                if (child.tag === 'button') {
//                    $buttons.append(self._renderHeaderButton(child));
//                }
//                if (child.tag === 'div' && child.attrs.class === 'print-direct') {
//                    $buttons.append(self._renderPrintButton(child));
//                }
//                if (child.tag === 'div' && child.attrs.class === 'print_date_revenue_report') {
//                    $buttons.append(self._renderReportButton(child));
//                }
//                if (child.tag === 'div' && child.attrs.class === 'print-picking-receipt') {
//                    $buttons.append(self._renderPicking_Receipt(child));
//                }
//            });
//            return $buttons;
//        }
    });
});
