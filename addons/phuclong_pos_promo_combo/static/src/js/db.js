odoo.define('phuclong_pos_promo_combo.db', function (require) {
	"use strict";
	var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');

	PosDB.include({
		init: function(options){
	        options = options || {};
			this.list_combo = [];
			this.combo_lines = [];
			this.combo_lines_detail = [];
	        this._super(options);
		},
		get_combo_by_id: function(combo_id){
			var combo_list = this.list_combo;
			if (combo_list){
				var combo = combo_list.filter(function(combo){return combo.id ==combo_id});
				if(combo.length){
					return combo[0]
				}
			}
			return false;
		},
		get_product_by_combo: function(combo_id, order=false){
			var self = this;
			var combo = this.list_combo.filter(function(combo){return combo.id == combo_id})
			var lines = [];
			var products = [];
			if (combo.length > 0 && (!combo[0].sale_type_ids.length || combo[0].sale_type_ids.indexOf(order.sale_type_id)>=0)){
				var comboline_ids = combo[0].combo_line_ids;
				_.each(comboline_ids, function(line_id){
					var line_object = self.combo_lines.filter(function(line){
						return line.id == line_id;
					})
					lines.push(line_object[0]);
				})
				var orderlines = [];
				if (order){
					orderlines = order.orderlines.models.filter(function(line){
						return line.combo_id == combo_id && line.is_done_combo == false;
					});
				}
				_.each(lines, function(line){
					var sum_line_qty = 0;
					var combo_line_used = [];	
					for (var i=0;i<orderlines.length;i++){
						var product = orderlines[i].product;
						if(orderlines[i].waiting_combo_line_id){
							if(line.id == orderlines[i].waiting_combo_line_id){
								if(line.qty_combo <= orderlines[i].quantity){
									lines = lines.filter(function(item){
										return item != line;
									});
									combo_line_used.push(orderlines[i].waiting_combo_line_id);
								}else{
									sum_line_qty = sum_line_qty + orderlines[i].quantity;
								}
							}
						}else{
							if(line.product_list_ids.indexOf(product.id)>=0 && !combo_line_used.includes(line.id)){
								orderlines[i].waiting_combo_line_id = line.id;
								if(line.qty_combo <= orderlines[i].quantity){
									lines = lines.filter(function(item){
										return item != line;
									});
									combo_line_used.push(line.id);
								}else{
									sum_line_qty = sum_line_qty + orderlines[i].quantity;
								}
							}
						}
					}
					if(sum_line_qty >= line.qty_combo){
						lines = lines.filter(function(item){
							return item != line;
						});
//						for (var i=0;i<orderlines.length;i++){
//							if(!orderlines[i].waiting_combo_line_id){
//								orderlines[i].waiting_combo_line_id = line.id;
//							}
//						}
						combo_line_used.push(line.id)
					}
				});
				//Vuong: only seach product on one line combo
				var line = lines[0]
				if(line){
					for (var i = 0; i< line.product_list_ids.length; i++){
						if (products.indexOf(line.product_list_ids[i]) < 0){
							products.push(line.product_list_ids[i]);
						}
					}
				}
			}
			return products;
		},
		// Thai: Tìm SP theo danh mục product.category
		get_product_by_cate_id: function(dom,products){
			var res = products;
			var product_db = this.product_by_id;
			var category_list = dom;
			_.each(product_db, function(product){
				if ((category_list.includes(product.categ_id[0])) && (res.indexOf(product.id) < 0)){
					res.push(product.id);
				}
			})
			return res;
		}
    });
});