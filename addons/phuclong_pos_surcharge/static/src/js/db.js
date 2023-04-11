odoo.define('phuclong_pos_surcharge.db', function (require) {
	"use strict";
	var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');

	PosDB.include({
		init: function(options){
	        options = options || {};
			this.surcharge_header = {};
			this.surcharge_line = {};
	        this._super(options);
		},
    });
});