odoo.define('phuclong_stock.InventoryUpdateController', function (require) {
"use strict";

var core = require('web.core');
var PivotController = require('web.PivotController');

var _t = core._t;
var qweb = core.qweb;


var InventoryUpdateController = PivotController.extend({
    events: _.extend({
        'click .o_button_update_inventory': '_onUpdateInventory'
    }, PivotController.prototype.events),

    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var $updateButton = $(qweb.render('Inventory.Update'));
        $node.find('.o_pivot_download').after($updateButton);
    },

    _onUpdateInventory: function () {
        var self = this;
        var prom = Promise.resolve();

        prom.then(function () {
            self._rpc({
                model: 'stock.quant',
                method: 'update_stock_qty',
                args: []
            }).then(function (res) {
                self.do_notify("Thông báo", "Cập nhật tồn kho thành công","sticky","");
            });
        });
    },
});

return InventoryUpdateController;

});
