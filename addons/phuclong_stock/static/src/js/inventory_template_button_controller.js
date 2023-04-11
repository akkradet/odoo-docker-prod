odoo.define('phuclong_stock.InventoryTemplateController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var _t = core._t;
var qweb = core.qweb;

var InventoryTemplateController = ListController.extend({
    events: _.extend({
        'click .o_button_template_inventory': '_onTemplateInventory'
    }, ListController.prototype.events),
    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        var context = renderer.state.getContext();
        this.inventory_id = context.active_id;
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        var $validationButton = $(qweb.render('InventoryLines.Template'));
        $validationButton.prependTo($node.find('.o_list_buttons'));
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handler called when user click on validation button in inventory lines
     * view. Makes an rpc to try to validate the inventory, then will go back on
     * the inventory view form if it was validated.
     * This method could also open a wizard in case something was missing.
     *
     * @private
     */
    _onTemplateInventory: function () {
        var self = this;
        var prom = Promise.resolve();
        var recordID = this.renderer.getEditableRecordID();
//        if (recordID) {
//            // If user's editing a record, we wait to save it before to try to
//            // validate the inventory.
//            prom = this.saveRecord(recordID);
//        }

        prom.then(function () {
            self._rpc({
                model: 'stock.inventory',
                method: 'action_template',
                args: [self.inventory_id]
            }).then(function (res) {
                var exitCallback = function (infos) {
                	return self.do_action(res);
                };
                return exitCallback();
            });
        });
    },
});

return InventoryTemplateController;

});
