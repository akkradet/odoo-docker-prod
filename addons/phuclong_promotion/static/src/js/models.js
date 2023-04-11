odoo.define('phuclong_promotion.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var _t = core._t;
    
    models.load_fields('sale.promo.header',['sale_type_ids', 'day_of_week', 'pos_payment_method_id']);
    models.load_fields('product.pricelist',['sale_type_ids','is_dollar_pos','card_code_pricelist']);
	models.load_fields('res.partner', 'card_code_pricelist_id');
	models.load_fields('sale.promo.lines',['amount_discount_limit', 'same_price', 'product_benefit_ids', 'count_discount_limit']);
    models.load_models([
        {
        	model: 'day.of.week.config',
            fields: ['value'],
            loaded: function(self,days_of_week){
            	self.days_of_week = days_of_week; 
            },
        },{
        	model: 'sale.promo.lines.benefit',
            fields: ['product_ids', 'allow_additional_price', 'additional_price', 'product_qty'],
			domain: function(self){ 
	        	return [['promo_line_id','in',self.promotion_lines_ids]];
	        },
            loaded: function(self, promo_benefit_lines){
            	self.promo_benefit_lines = promo_benefit_lines; 
            },
        }
    ]);
    
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this,arguments);
            this.payment_promotion_id = this.payment_promotion_id || false;
        },
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
//            json.note_label = this.note_label;
            return json;
        },
        init_from_JSON: function(json){
            _super_order.init_from_JSON.apply(this,arguments);
//            this.note_label = json.note_label;
        },
        
        check_pricelist_item: function(item){
			var self = this;
        	var pricelist = self.get_pricelist_by_id(item.pricelist_id[0]);
        	if(pricelist.sale_type_ids.length && !pricelist.sale_type_ids.includes(self.sale_type_id)){
        		return false;
        	}
        	if(pricelist.is_dollar_pos != self.pos.config.is_dollar_pos){
        		return false;
			}
			if (self.linked_draft_order_be){
				return false;
			}
			//pricelist by cardcode
			var partner = self.get_client();
			if(partner && partner.card_code_pricelist_id){
				if(partner.card_code_pricelist_id[0] != pricelist.id){
					return false;
				}
			}else{
				if(pricelist.card_code_pricelist){
					return false;
				}
			}
    		return true;
    	},
        
        check_promo_header: function(promotion_header){
        	var self = this;
        	if(promotion_header.sale_type_ids.length && !promotion_header.sale_type_ids.includes(self.sale_type_id)){
        		return false;
        	}
        	if(promotion_header.day_of_week.length){
        		var today = new Date();
	    		var weekday = [];
	    		weekday[0] = "sunday";
	    		weekday[1] = "monday";
	    		weekday[2] = "tuesday";
	    		weekday[3] = "wednesday";
	    		weekday[4] = "thursday";
	    		weekday[5] = "friday";
	    		weekday[6] = "saturday";
	    		var current_day_of_week = weekday[today.getDay()];
	    		var current_day_of_week_id = false;
	    		for(var day in self.pos.days_of_week){
	    			if(self.pos.days_of_week[day].value == current_day_of_week){
	    				current_day_of_week_id = self.pos.days_of_week[day].id;
	    			}
	    		}
	    		if(current_day_of_week_id && !promotion_header.day_of_week.includes(current_day_of_week_id)){
	    			return false;
	    		}
        	}
			//promotion by payment
			if(promotion_header.pos_payment_method_id && promotion_header.pos_payment_method_id[0] != this.payment_promotion_id){
				return false;
			}
			if(!promotion_header.pos_payment_method_id && this.payment_promotion_id){
				return false;
			}
    		return true;
    	},
    	
    	compute_promotion: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.orderlines;
        	
    		if (orderlines.length ==0) {
        		return;
        	}
    		
    		var check_return_promo = order.get_return_promotion();
    		if(!check_return_promo){
    			return;
    		}

			if(order.check_order_payment_on_account() || order.check_order_payment_voucher()){
				return;
			}
			
			var client = order.get_client();
			if(client && client.card_code_pricelist_id){
				return;
			}
    		
			order.promotion_id = false;
			order.remove_discount_manual_all_order();
    		order.set_discount_amount(0);
//    		order.set_promotion_all_order(false);
    		
    		var promotion_lines = order.get_promotion();
    		if (promotion_lines){
    			var promo_ids = [];
    	    	for (var i=0;i<promotion_lines.length;i++){
    	    		if(promotion_lines[i].promotion_id!=false){
    	    			promo_ids.push(promotion_lines[i]); 
    	    		}
    	    	}
    	    	for (var i=0;i<promotion_lines.length;i++){
    				var promo_header_id = []
    				if(promotion_lines[i].discount_id!=false){
    					promo_header_id = promotion_lines[i].discount_id; 
    				}else{
    					promo_header_id = promotion_lines[i].promotion_id; 
    				}
    				var promo_header = order.get_promo_header_by_id(promo_header_id[0]);
    				if(promo_header!=false && promotion_lines[i].discount_id){
    					order.get_promotion_by_line(promo_ids,promotion_lines[i],0)
    				}
    			}
    	    	if(promo_ids.length){
    	    		promo_ids = _.sortBy(promo_ids,function(line){return line.benefit_type;});
    	    		order.get_promotion_by_line(promo_ids,promo_ids[0],0)
    	    	}
    		}
    	},
    	
    	show_popup_promotion: function(product,lists,promotion_loop_type,promo_ids,promo_line,qty_rewared,benefit_qty_total,benefit_lines,promotion_price){
    		var self = this
    		var order = this.pos.get_order();
    		if(product.default_code == 'reward_code'){
    			var line_id = new models.Orderline({}, {pos: this.pos, order: order, product: product});
            	line_id.set_uom(product.uom_id);
            	line_id.set_quantity_no_compute(benefit_qty_total);
				order.get_new_price(product,benefit_qty_total,line_id);
            	line_id.set_unit_price(0);
            	line_id.set_is_promotion_line();
            	line_id.set_promotion(promo_line.promotion_id, promo_line.id);
            	line_id.set_barcode_uom_relation(product.barcode);
    			order.orderlines.add(line_id);
    		}else{
    			return this.pos.chrome.gui.show_popup('topping_poppup',{
        			'is_promotion_product':true,
                    'product': product,
                    'lists_template_promo': lists,
                    'promotion_loop_type': promotion_loop_type,
                    'promotion_ids': promo_ids,
                    'promo_line': promo_line,
                    'qty_rewared': qty_rewared,
                    'benefit_qty_total': benefit_qty_total,
					'benefit_lines': benefit_lines,
					'promotion_price':promotion_price,
                });
    		}
    	},
    	
    	choose_multi_product: function(lists_raw,promo_ids,promo_line,qty_rewared,benefit_qty_total,benefit_lines=[]){
        	var self = this;
			var lists = []
			_.each(lists_raw, function(promo_product){
				if(self.pos.db.locked_product.indexOf(promo_product.item) < 0){
					lists.push(promo_product);
				}
			})
        	var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
        	var promotion_loop_type = 'none';
        	var choose_multi_promotion = false;
        	var check_price_list = [];
			var list_product_promotion = lists;
			var condition_line = false;
			var condition_product = false;
			var max_price_promotion = 0;
			var promotion_price = 0;

			if(promo_line.product_attribute != 'order' && promo_line.same_price && promo_line.benefit_type != 'combo_product'){
				var price_array = [];
		    	var conditon_lines = orderlines.filter(function(line) 
					{return line.is_condition_line == true && line.promotion_condition_id == promo_line.promotion_id[0] && line.quantity > 0;}
				);
				if(conditon_lines.length){
					conditon_lines = _.sortBy(conditon_lines,function(line){return line.id;}).reverse();
					for(var i in conditon_lines){
						for(var j=0; j< conditon_lines[i].quantity; j++){
							price_array.push(conditon_lines[i]);
						}
					}
				}
				//Check max price
				if(price_array.length && price_array.length >= benefit_qty_total){
					condition_line = price_array[benefit_qty_total-1];
					max_price_promotion = condition_line.price;
				}
				if(max_price_promotion){
					for(var l in lists){
						var product_reward = this.pos.db.product_ids_by_tmpl_id[lists[l].item] || false;
						if(product_reward.length && product_reward[0].lst_price <= max_price_promotion){
							check_price_list.push(lists[l]);
						}
					}
				}
				if(condition_line){
					condition_product = condition_line.product.display_name;
				}
				list_product_promotion = check_price_list;
			}

//			if(check_price_list.length){
//				list_product_promotion = check_price_list;
//			}
			
        	if(lists.length>1){
        		benefit_qty_total -= 1;
        	}
			if(benefit_qty_total>0 && lists.length>1){
				//loop if more than 1 product template available
				promotion_loop_type = 'multi_product';
//				self.choose_multi_product(lists,promo_ids,promo_line,qty_rewared,benefit_qty_total);
			}else{
				if(promo_line.benefit_type == 'combo_product' && benefit_lines.length>1){
					//loop if more than 1 promotion available
					benefit_lines.shift();
					promotion_loop_type = 'multi_benefit_lines';
				}else{
					//loop if more than 1 promotion available
					if(promo_ids.length>1){
						var promo_temp = [];
						for(var i in promo_ids){
							if(promo_ids[i].id != promo_line.id){
								promo_temp.push(promo_ids[i]);
							}
						}
						if(promo_temp[0].modify_type == 'pro_goods' && (promo_temp[0].benefit_type == 'cat' || 
						promo_temp[0].benefit_type == 'list_product_template' || promo_temp[0].benefit_type == 'product_template')){
	//						self.get_promotion_by_line(promo_temp,promo_temp[0],qty_rewared);
							promo_ids = promo_temp;
							promotion_loop_type = 'multi_promotion';
						}
					}
				}
			}
        	if(lists.length==1){
        		var product = self.pos.db.product_ids_by_tmpl_id[lists[0].item] || [];
        		if(product.length){
        			self.show_popup_promotion(product[0],lists,promotion_loop_type,promo_ids,promo_line,qty_rewared,benefit_qty_total,benefit_lines,promotion_price);
        		}
    			return true;
    		}
        	this.pos.chrome.gui.show_popup('selection_promo',{
    			'title': _t('Vui lòng chọn mã quà tặng !'),
    			'list': list_product_promotion,
				'limit': max_price_promotion,
				'promo_line': promo_line,
				'condition_product': condition_product,
    			'confirm':function(product_template){
					//add price != 0 from addtion promotion combo
					if(promo_line.benefit_type == 'combo_product'){
						_.each(promo_line.product_benefit_ids, function(line){
							var additional_price_benefit_line = self.pos.promo_benefit_lines.filter(function(l){
								return l.id == line && l.allow_additional_price;
							})
							if(additional_price_benefit_line.length){
								additional_price_benefit_line = additional_price_benefit_line[0];
								if(additional_price_benefit_line.product_ids.includes(product_template)){
									promotion_price = additional_price_benefit_line.additional_price;
								}
							}
						})
					}
//    				self.choose_reward_from_template(promo_ids,product_template,promo_line,qty_rewared,true);
    				var product = self.pos.db.product_ids_by_tmpl_id[product_template] || [];
    				if(product.length){
    					self.show_popup_promotion(product[0],lists,promotion_loop_type,promo_ids,promo_line,qty_rewared,benefit_qty_total,benefit_lines,promotion_price);
    				}
    				return true;
    			},
    		});
    	},
    	
    	check_for_line_no_condition: function(promo_line, set_condition, orderline_selected){
    		var self = this;
    		var orderlines = this.get_orderline_no_promotion();
    		if(orderline_selected){
    			orderlines = orderline_selected;
    		}
    		var result = false;
    		var val2 = 0;
    		var promotion_id = false;
    		//check to set condition line
//    		var set_condition = true;
    		if(promo_line.promotion_id){
    			promotion_id = promo_line.promotion_id;
//    			set_condition = true;
    		}else{
    			promotion_id = promo_line.discount_id;
    		}
    		
    		if (promo_line.product_attribute == 'product' || promo_line.product_attribute == 'product_template'){
    			var item = 0;
    			var condition_lines = [];
    			for (item in orderlines){
    				var orderline = orderlines[item];
    				if(orderline.quantity<0 || orderline.is_manual_discount){
    					continue;
    				}
    				var check_product = false;
    				if(promo_line.product_attribute == 'product'){
    					var orderline_ean = orderline.barcode_uom_relation || orderline.product.barcode;
    					if(promo_line.product_id[0] == orderline.product.id && promo_line.product_ean == orderline_ean){
    						check_product = true;
    					}
    				}else{
    					if(promo_line.product_tmpl_id[0] == orderline.product.product_tmpl_id){
    						check_product = true;
    					}
    				}
    				if (check_product==true){
    					condition_lines.push(orderline);
    				}
    			}
    			if(condition_lines.length){
    				for (var i in condition_lines){
    					var orderline = condition_lines[i];
    					if(promo_line.volume_type == 'qty'){
    						val2 += orderline.quantity;
    					}else if(promo_line.volume_type == 'amt'){
    						val2 += orderline.get_base_display_price();
    					}else if(promo_line.volume_type == 'amtx'){
    						val2 += orderline.get_price_without_tax();
    					}
    				}
    				result = self.check_condition(val2,promo_line);
    				if(result == true){
    					if(set_condition){
    						for (var i in condition_lines){
    							condition_lines[i].set_condition_line(promotion_id, promo_line.id);
    							condition_lines[i].set_disable_promotion(false);
    						}
    					}else{
    						for (var i in condition_lines){
    							condition_lines[i].set_promotion_available(true);
    						}
    					}
    					if (promo_line.modify_type == 'disc_percent' || promo_line.modify_type == 'disc_value'){
    						return true;
    					}
    					promo_line.computed_benefit_qty = promo_line.benefit_qty;
    					if(promo_line.break_type == 'Recurring' && val2 >0){
    						promo_line.computed_benefit_qty = parseInt(val2 /promo_line.value_from * promo_line.benefit_qty);
							if(promo_line.value_from == 0){
								promo_line.computed_benefit_qty = promo_line.benefit_qty;
							}
    						if (promo_line.computed_benefit_qty == 0){
    							return false;
    						}
    					}
    				}
    				return result;
    			}
    		}else if(promo_line.product_attribute == 'cat' || promo_line.product_attribute == 'list_cat'){
    			var item = 0;
    			var categ_qty = 0;
    			var categ_amt = 0;
    			var categ_amtx = 0;
    			
    			for (item in orderlines){
    				var orderline = orderlines[item];
    				if(orderline.quantity<0 || orderline.is_manual_discount){
    					continue;
    				}
//    				if (orderline.product.categ_id[0] == promo_line.categ_id[0]){
    				var category_list = JSON.parse(promo_line.categories_dom);
    				if (category_list.includes(orderline.product.categ_id[0])){
    					categ_qty += orderline.quantity;
    					categ_amt += orderline.get_base_display_price();
    					categ_amtx += orderline.get_price_without_tax();
    				}
    			}
    			if (categ_qty != 0){
    				if(promo_line.volume_type == 'qty'){
    					val2 = categ_qty;
    				}else if(promo_line.volume_type == 'amt'){
    					val2 = categ_amt;
    				}else if(promo_line.volume_type == 'amtx'){
    					val2 = categ_amtx;
    				}
    				result = self.check_condition(val2,promo_line);
    				if(result == true){
						for (item in orderlines){
							var orderline = orderlines[item];
							if(orderline.quantity<0 || orderline.is_manual_discount){
								continue;
							}
							var category_list = JSON.parse(promo_line.categories_dom);
							if (category_list.includes(orderline.product.categ_id[0])){
								if(set_condition){
									orderline.set_condition_line(promotion_id, promo_line.id);
    								orderline.set_disable_promotion(false);
								}else{
									orderline.set_promotion_available(true);
		    					}
							}
						}
    					promo_line.computed_benefit_qty = promo_line.benefit_qty;
    					if(promo_line.break_type == 'Recurring' && orderline.quantity >0){
    						promo_line.computed_benefit_qty = parseInt(val2 /promo_line.value_from * promo_line.benefit_qty);
							if(promo_line.value_from == 0){
								promo_line.computed_benefit_qty = promo_line.benefit_qty;
							}
    						if (promo_line.computed_benefit_qty == 0){
    							return false;
    						}
    					}
    				}
    				return result;
    			}else{
    				return false;
    			}
    		}else if(promo_line.product_attribute == 'combo'){
    			var item = 0;
    			var combo_qty = 0;
    			var combo_amt = 0;
    			var combo_amtx = 0;
    			var product_list = [];
    			for(var i in promo_line.product_ids){
    				product_list.push(promo_line.product_ids[i]);
    			}
    			var product_lines = [];
    			var combo_product = [];
    			for (item in orderlines){
    				var orderline = orderlines[item];
    				if(orderline.quantity<0 || orderline.is_manual_discount){
    					continue;
    				}
    				product_lines.push(orderline.product.id);
    				if (product_list.includes(orderline.product.id) && orderline.is_combo_line==false){
    					//cross sale case
//    					if(promo_line.value_from == 0){
//    						if(product_lines.length){
//    							if(!product_lines.includes(orderline.product.id)){
//    								product_lines.push(orderline.product.id);
//    							}
//    						}else{
//    							product_lines.push(orderline.product.id);
//    						}
//    					}
    					combo_qty += orderline.quantity;
    					combo_amt += orderline.get_base_display_price();
    					combo_amtx += orderline.get_price_without_tax();
    					combo_product.push(orderline)
    				}
    			}
//    			if(promo_line.value_from == 0 && product_lines.length){
//    				var check_products = [];
//    				for (item in product_list){
//    					var product_id = product_list[item];
//    					if(check_products.length){
//    						if(!check_products.includes(product_id)){
//    							check_products.push(product_id);
//    						}
//    					}else{
//    						check_products.push(product_id);
//    					}
//    				}
//    				if(!(product_lines.length == check_products.length)){
//    					return false
//    				}
//    			}
    			
    			if (combo_qty != 0){
    				if(promo_line.volume_type == 'qty'){
    					val2 = combo_qty;
    				}else if(promo_line.volume_type == 'amt'){
    					val2 = combo_amt;
    				}else if(promo_line.volume_type == 'amtx'){
    					val2 = combo_amtx;
    				}
    				result = self.check_condition(val2,promo_line);
    				if(result == true){
    					if(set_condition){
    						for(var line in combo_product){
    							combo_product[line].set_condition_line(promotion_id, promo_line.id);
    							combo_product[line].set_disable_promotion(false);
    						}
    					}else{
    						for(var line in combo_product){
    							combo_product[line].set_promotion_available(true);
    						}
    					}
    					promo_line.computed_benefit_qty = promo_line.benefit_qty;
    					if(promo_line.break_type == 'Recurring' && orderline.quantity >0){
    						promo_line.computed_benefit_qty = parseInt(val2 /promo_line.value_from * promo_line.benefit_qty);
							if(promo_line.value_from == 0){
								promo_line.computed_benefit_qty = promo_line.benefit_qty;
							}
    						if (promo_line.computed_benefit_qty == 0){
    							return false;
    						}
    					}
    				}
    				return result;
    			}else{
    				return false;
    			}
    		}
    		return false;
    	},
    	
    	check_for_order_no_condition:function(promo_line, set_condition ,orderline_selected){
    		var self = this;
    		var val2 = 0;
    		var orderlines = this.get_orderlines();
    		if(orderline_selected){
//    			orderlines = this.get_orderline_no_promotion();
    			
//    			for(var i in orderline_selected){
//					if(!orderlines.includes(orderline_selected[i])){
//						orderlines.push(orderline_selected[i]);
//					}
//    			}
				//Use only selected line to check
//				orderlines = orderline_selected;
				orderlines = [];
				for(var i in orderline_selected){
					orderlines.push(orderline_selected[i]);
				}
				

    			var total_orderlines = this.get_orderlines();
    			for(var i in total_orderlines){
    				if(total_orderlines[i].promotion_all_order_id){
						if(total_orderlines[i].promotion_line_id == promo_line.id){
							orderlines.push(total_orderlines[i]);
						}else{
							if(promo_line.modify_type != 'pro_goods'){
								orderlines.push(total_orderlines[i]);
							}
						}
					}
    			}
    		}
    		if (promo_line.volume_type == 'qty'){
    			var item = 0;
    			var qty = 0;
//    			var orderlines = this.get_orderlines();
    			for (var i=0; i < orderlines.length; i++){
    				qty += orderlines[i].quantity;
    			}
    			val2 = qty;
    		}else if(promo_line.volume_type == 'amt'){
    			var amount_total = this.get_total_with_tax();
    			if(promo_line.check_orgin_price){
    				amount_total = 0;
    				for(var line in orderlines){
    					amount_total += orderlines[line].get_base_display_price();
    				}
    			}
    			val2 = amount_total;
    		}else if(promo_line.volume_type == 'amtx'){
    			val2 = this.get_total_without_tax();
    		}
    		
    		var result = self.check_condition(val2 , promo_line);
    		
    		if(result == true){
    			if(promo_line.promotion_id){
    				if(set_condition){
    					for(var line in orderlines){
        					orderlines[line].set_condition_line(promo_line.promotion_id, promo_line.id);
        				}
    				}
    			}
    			if(!set_condition){
					for(var line in orderlines){
    					orderlines[line].set_promotion_available(true);
    				}
				}
    			if (promo_line.parent_line_id){
    				return true;
    			}
    			if (promo_line.modify_type == 'disc_percent' || promo_line.modify_type == 'disc_value'){
    				return true;
    			}
    			if(promo_line.break_type == 'Recurring'){
    				promo_line.computed_benefit_qty = parseInt(val2 /promo_line.value_from * promo_line.benefit_qty);
					if(promo_line.value_from == 0){
						promo_line.computed_benefit_qty = promo_line.benefit_qty;
					}
    				if (promo_line.computed_benefit_qty == 0){
    					return false;
    				}
    			}
    			if(promo_line.break_type == 'Point'){
    				promo_line.computed_benefit_qty = promo_line.benefit_qty;
    				if (promo_line.computed_benefit_qty == 0){
    					return false;
    				}
    			}
    		}
    		return result;
    	},
    	
    	check_promoline_no_condition: function(promo_line, set_condition, orderline_selected){
    		var self= this;
    		if (promo_line.product_attribute == 'order'){
    			return self.check_for_order_no_condition(promo_line, set_condition, orderline_selected);
    		}else{
    			return self.check_for_line_no_condition(promo_line, set_condition, orderline_selected);
    		}
    	},
    	
    	check_promotion_no_condition: function(promo_line, set_condition, orderline_selected){
    		var self = this;
    		var branch_lines = promo_line; 
    		var passed = false;
    		var promo_stack = [];
    		for(var i=0;i<branch_lines.length;i++){
    			if(i==0){
    				passed = true;
    			}
    			var line = branch_lines[i];
    			var result = self.check_promoline_no_condition(line, set_condition, orderline_selected);
    			if (branch_lines[i].logical == 'and'){
    				passed = eval(String(passed) + '&&' + String(result))
    			}else if (branch_lines[i].logical == 'or'){
    				promo_stack.push(passed);
    				passed = true;
    				passed = eval(String(passed) + '&&' + String(result))
    			}
    			if(i == branch_lines.length -1 && branch_lines[i].logical == 'and'){
    				promo_stack.push(passed);
    			}
    		}
    		_.each(promo_stack,function(item){
    			passed = eval(String(passed) + '||' + String(item));
    		});
    		if (passed == false){
    			return false;
    		}else{
    			var get_promoline = branch_lines[0];
    			return get_promoline;
    		}
    	},
    	
    	get_promotion_no_condition: function(set_condition=false, orderline_selected=false){
    		var self = this;
    		var orderlines = this.get_orderlines();
    		
    		//Return promotion coupon if exist
    		var geted_promotions = []
    		var promotion_coupon = self.get_promotion_for_coupon();
    		if(!promotion_coupon.length && self.coupon_code_array.length){
    			return geted_promotions;
    		}
    		if(promotion_coupon.length){
    			for(var i in promotion_coupon){
    				var promo_line = promotion_coupon[i];
    				var line = self.check_promotion_no_condition([promo_line], set_condition, orderline_selected);
    				if(line){
    					geted_promotions.push(line);
    				}
    			}
    			return geted_promotions;
    		}
    		
    		var now = new Date();
    		now.format("yy/M/dd");
    		var hours = now.getHours();
    		var minute = now.getMinutes();
    		var float_now = hours + minute/60;
    		var apply_any_time = false;
    		
    		var all_promotion_lines = []
    		var all_promotion_lines_order = []
    		
    		for (var i = 0; i< this.pos.promotion_header.length;i++){
    			var header = this.pos.promotion_header[i];
    			if(header.use_for_coupon){
    				continue;
    			}
    			//custom check
    			var check_promo_header = self.check_promo_header(header) || false;
    			if(!check_promo_header){
    				continue;
    			}
    			//check by partner_category
    			if(header.member_category.length){
    				var partner = this.get_client() || false;
    				if(!partner){
    					continue;
    				}
    				if(!partner.category_id){
    					continue;
    				}
    				for(var categ in partner.category_id){
    					if(header.member_category.includes(partner.category_id[categ])){
    						break;
    					}
    					continue;
    				}
    			}
    			
    			if ((header.start_hour == header.end_hour) && header.start_hour == 0){
    				apply_any_time = true;
    			}
    			if ((header.start_hour <= float_now && header.end_hour >= float_now) || apply_any_time == true){
    				var promotion_lines = [];
    				if (header.list_type == 'DIS'){
    					promotion_lines = header.discount_line;
    				}else{
    					promotion_lines = header.promo_line;
    				}
    				_.each(promotion_lines,function(item){
    					if (item){
    						var promo_line_id = self.pos.promotion_lines[item];
    						if(promo_line_id!=undefined && promo_line_id.length){
    							if(promo_line_id[0].product_attribute=='order'){
    								all_promotion_lines_order.push(promo_line_id[0]);
    							}else{
    								all_promotion_lines.push(promo_line_id[0]);
    							}
    						}
    					}
    				});
    			}
    		}
    		//Sort promotion_line
    		if(all_promotion_lines.length){
    			all_promotion_lines = _.sortBy(all_promotion_lines,function(line){
    				return [line.value_from, eval(line.discount_id != false).toString(), line.product_attribute, line.start_date_active, (10000000000 + line.discount_value)]
    			}).reverse();
//    			all_promotion_lines = _.sortBy(all_promotion_lines,function(line){return line.discount_id[0]});
    			for(var i in all_promotion_lines){
    				var promo_line = all_promotion_lines[i];
    				var line = self.check_promotion_no_condition([promo_line], set_condition, orderline_selected);
    				if(line){
    					if(set_condition){
    						for(var l in orderline_selected){
        						orderline_selected[l].set_disable_promotion(false);
        					}
    					}
    					geted_promotions.push(line);
    				}
    			}
    		}
    		
    		//Sort promotion_line all order
    		if(all_promotion_lines_order.length){
    			all_promotion_lines_order = _.sortBy(all_promotion_lines_order,function(line){
    				return [line.value_from, eval(line.discount_id != false).toString(), line.product_attribute, line.start_date_active, (10000000000 + line.discount_value)]
    			});
    			for(var i in all_promotion_lines_order){
    				var promo_line = all_promotion_lines_order[i];
    				var line = self.check_promotion_no_condition([promo_line], set_condition, orderline_selected);
    				if(line){
    					if(set_condition){
    						for(var l in orderline_selected){
        						orderline_selected[l].set_disable_promotion(false);
        					}
    					}
    					geted_promotions.push(line);
    				}
    			}
    			
    		}
    		
    		return geted_promotions;
    	},

		get_promotion_discount_limit_qty: function(promo_line){
			return promo_line.count_discount_limit || 0;
		},

		get_promotion_by_line: function(promo_ids,promo_line,qty_rewared){
			var self = this;
			if (promo_line.modify_type == 'pro_goods' && promo_line.benefit_type=='combo_product' && promo_line.product_benefit_ids.length>0){
				if(promo_line.break_type == 'Point'){
					var promotion_line_exist = this.get_orderlines().filter(function(line) 
						{return line.promotion_line_id == promo_line.id && line.is_promotion_line}
					);
					if(promotion_line_exist.length){
						return
					}
				}
				var template_lists = [];
				var benefit_lines = [];
				var check_push_product_first_line = false;
				_.each(promo_line.product_benefit_ids, function(line){
					var benefit_line = self.pos.promo_benefit_lines.filter(function(l){
						return l.id == line;
					})
					if(benefit_line.length){
						benefit_line = benefit_line[0];
						if(!check_push_product_first_line || benefit_line.allow_additional_price){
							var reward_product_tmpls = benefit_line.product_ids || [];
							for(var tmpl in reward_product_tmpls){
								var product_template_id = reward_product_tmpls[tmpl];
								var product_template = self.pos.product_templates[product_template_id];
								template_lists.push({
				    				label : product_template.default_code + ' - ' + product_template.name,
				    				item: product_template.id,
				    			});
							}
						}
						if(!benefit_line.allow_additional_price){
							benefit_lines.push(benefit_line);
							check_push_product_first_line = true;
						}
					}
				})
				if(benefit_lines.length){
					var computed_benefit_qty = benefit_lines[0].product_qty*promo_line.computed_benefit_qty;
					self.choose_multi_product(template_lists,promo_ids,promo_line,qty_rewared,computed_benefit_qty,benefit_lines);
				}
				return true;
			}
			var result = _super_order.get_promotion_by_line.apply(this,arguments);
			if(promo_line.product_attribute=='order' && promo_line.modify_type == 'disc_percent' && promo_line.amount_discount_limit){
				if(this.discount_amount && Math.abs(this.discount_amount) > promo_line.amount_discount_limit){
					this.set_discount_amount(-promo_line.amount_discount_limit);
				}
			}
			return result
		},
		
		//Reset promotion no rerender line
		reset_promotion_line_no_render: function(promotion_line_id){
			var order = this.pos.get_order();
	    	var orderlines = order.orderlines;
	    	
			var same_promo_lines = orderlines.filter(function(line) 
					{return line.promotion_line_id == promotion_line_id}
			);
			for(var i in same_promo_lines){
				var line = same_promo_lines[i];
				if (line.is_promotion_line){
		 		    order.remove_orderline(line);
		 		    i -= 1;
	 		 	}else{
	 		 		if(line.product.lst_price != 0){
	 		 			line.remove_discount_line_no_render(true);
	 		 		}
	 		 	}
				order.get_new_price(line.product, line.quantity, line);
			}
		},
		
		check_promotion_all_order: function(){
	    	var orderlines = this.get_orderlines();
	    	for (var i=0; i < orderlines.length; i++){
	    		if(orderlines[i].promotion_all_order_id){
	    			return true;
	    		}
	    	}
	    	return false;
	    	
	    },

		check_all_order_with_other_promo: function(){
	    	var orderlines = this.get_orderlines();
			var promotion_all_order_lines = orderlines.filter(function(l){
				return l.promotion_all_order_id
			})
			if(promotion_all_order_lines.length){
				var promotion_line_id = promotion_all_order_lines[0].promotion_line_id;
				var other_promotion = orderlines.filter(function(l){
					return l.loyalty_discount_percent || l.is_promotion_line || (!l.promotion_all_order_id && l.promotion_line_id && l.promotion_line_id != promotion_line_id);
				})
				if(other_promotion.length){
					return true;
				}
			}
	    	return false;
	    },

		check_promotion_discount_limit: function(){
			var self = this;
	    	var orderlines = this.get_orderlines();
			var promotion_check = [];
			if(self.order_in_call_center && !self.pos.config.is_callcenter_pos){
				return false;
			}
			for(var i in orderlines){
				var line = orderlines[i];
				if(line.promotion_line_id && !promotion_check.includes(line.promotion_line_id)){
					promotion_check.push(line.promotion_line_id);
					var count_discount_limit = self.pos.promotion_lines[line.promotion_line_id][0].count_discount_limit;
					if(count_discount_limit){
						if(self.pos.promotion_lines[line.promotion_line_id][0].count_discount_limit){
							var same_promotion = orderlines.filter(function(l){
								return l.promotion_line_id == line.promotion_line_id;
							})
							var total_promo_qty = 0;
							_.each(same_promotion, function(promo){
								total_promo_qty += promo.get_quantity_str();
							})
							if(total_promo_qty > count_discount_limit){
								return true
							}
						}
					}
				}
			}
	    	return false;
	    },

		check_promotion_reward: function(){
			var self = this;
	    	var orderlines = this.get_orderlines();
//			var reward_orderline = orderlines.filter(function(item){
//                return item.product.default_code == 'reward_code';
//            })
			var promotion_list = [];
			if(orderlines.length){
				for(var i in orderlines){
					var line = orderlines[i];
					if(line.promotion_line_id){
						var promo_line = self.pos.promotion_lines[line.promotion_line_id][0];
						if(promo_line.modify_type == 'pro_goods' && promo_line.benefit_type == 'product_template' && promo_line.benefit_product_tmpl_id){
							var product = self.pos.db.product_ids_by_tmpl_id[promo_line.benefit_product_tmpl_id[0]] || [];
				    		if(product.length && product[0].default_code == 'reward_code' && !promotion_list.includes(line.promotion_line_id)){
								promotion_list.push(line.promotion_line_id);
							}
						}
					}
					
				}
			}
			if(promotion_list.length > 1){
				return true;
			}
			return false;
		}

    });
    
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
		remove_discount_line_no_render : function(force_remove=false){
			var order = this.pos.get_order();
			if(!order.check_condition_discount_line(this)){
				return;
			}
			if(this.is_manual_discount==true && !force_remove){
				return;
			}
	//		this.is_manual_discount = false;
			if (this.is_manual_discount){
				this.is_manual_discount = false
			}
			var product = this.product;
			var quantity = this.quantity;
			if(quantity < 0){
				return;
			}
	//		this.set_condition_line(false);
			this.is_condition_line = false;
			this.promotion_condition_id = false;
			this.promotion_id = false;
			this.promotion_line_id = false;
			this.set_promotion_all_order_line(false);
//			if(this.discount){
//				this.set_discount(0);
//			}
	        this.discount = 0;
	        this.discountStr = '' + 0;
//			if(this.discount_amount){
//				this.set_discount_amount_line(0);
//			}
        	this.discount_amount = 0;
			var rerender = false;
			this.set_price(product.list_price, rerender);
			order.get_base_price_by_line(product,quantity,this,true,rerender);	
		},
		
		get_base_display_price: function(){
			return this.get_quantity_str()*this.get_unit_display_price()
		},
    });
    
});

