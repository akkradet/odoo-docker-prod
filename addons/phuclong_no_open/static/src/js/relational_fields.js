odoo.define('phuclong_no_open.relational_fields', function (require) {
    "use strict";

    var relational_fields = require('web.relational_fields');

    var noOpens = {
        product_id: [
            'purchase.order.line',
            'stock.move',
            'stock.move.line',
            'product.material.line'
        ],
        line_id: [
            'pos.order.line.option',
        ],
        purchase_type_id: [
            'purchase.order'
        ],
        warehouse_id: [
            'pos.order'
        ],
        partner_loyalty_level_id: [
            'pos.order'
        ],
        cashier_id: [
            'pos.order'
        ],
		session_id: [
            'pos.order'
        ],
        reward_id: [
            'pos.order.line'
        ],
		product_uom: [
            'purchase.order.line'
        ],
		return_reason_id: [
            'purchase.order'
        ],
		picking_type_id: [
            'purchase.order'
        ],
		user_id: [
            'purchase.order'
        ],
		confirm_person_id: [
            'purchase.order'
        ],
		approved_person_id: [
            'purchase.order'
        ],
		location_id: ['stock.move', 'stock.move.line'],
		location_dest_id: ['stock.move', 'stock.move.line'],
		group_id: ['stock.move'],
		sequence_id: ['stock.picking.type'],
		product_uom_id: ['stock.move.line'],
		create_uid: ['pos.product.lock','warehouse.transfer'],

    };

    return relational_fields.FieldMany2One.include({
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            if (name in noOpens && record) {
                var self = this;
                noOpens[name].forEach(function (model) {
                    if (record.model == model) {
                        self.noOpen = true;
                    }
                });
            }
        }
    });
});