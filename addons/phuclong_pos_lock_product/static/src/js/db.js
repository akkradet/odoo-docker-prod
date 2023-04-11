odoo.define('phuclong_pos_lock_product.db', function (require) {
	"use strict";
	var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');

	PosDB.include({
		init: function(options){
	        options = options || {};
	    	this.locked_product = [];
	        this._super(options);
		},
		add_locked_product: function(lock_board){
			var self = this;
			var lock_board_products = lock_board ? lock_board[0]: false
			if (lock_board_products){
				_.each(lock_board_products.product_ids,function(statement){
					self.locked_product.push(statement);
				});
			}
		},
		check_is_locked: function(product_tmpl_id){
			if(this.locked_product.indexOf(product_tmpl_id) >= 0){
				return true;
			}
			var product = this.product_ids_by_tmpl_id[product_tmpl_id] || [];
    		if(product.length){
    			if(!['topping', 'food', 'drink', 'packaged_product'].includes(product[0].fnb_type)){
					return true;
				}
    		}
			return false;
		}
    });
});