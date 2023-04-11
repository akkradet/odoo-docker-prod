odoo.define('phuclong_pos_base.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var rpc = require('web.rpc');
    
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this,arguments);
            this.note_label = this.note_label || false;
            this.operation_history_list = this.operation_history_list || [];
            this.employee_cashregister = false;
            this.emp_coupon_code = this.emp_coupon_code || '';
            this.use_emp_coupon = this.use_emp_coupon || false;
        },
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
            json.note_label = this.note_label;
            json.operation_history_ids = this.get_operation_history_ids() || [];
            json.emp_coupon_code = this.emp_coupon_code;
            json.use_emp_coupon = this.emp_coupon_code ? true : false;
            return json;
        },
        init_from_JSON: function(json){
            _super_order.init_from_JSON.apply(this,arguments);
            this.note_label = json.note_label;
            this.emp_coupon_code = json.emp_coupon_code || '';
            this.use_emp_coupon = json.use_emp_coupon || false;
            this.current_coupon_code = json.emp_coupon_code || '';
        },
//		generate_unique_id: function() {
//	        // Generates a public identification number for the order.
//	        // The generated number must be unique and sequential. They are made 12 digit long
//	        // to fit into EAN-13 barcodes, should it be needed
//	
//	        function zero_pad(num,size){
//	            var s = ""+num;
//	            while (s.length < size) {
//	                s = "0" + s;
//	            }
//	            return s;
//	        }
//	        return zero_pad(this.pos.pos_session.id,6) +'-'+
//	               zero_pad(this.pos.pos_session.login_number,3) +'-'+
//	               zero_pad(this.sequence_number,4);
//	    },
        set_operation_history_list: function(operation){
            this.operation_history_list.push(operation);
            this.trigger('change',this);
        },
        get_operation_history_ids: function(){
        	var value_list = [];
        	if(this.operation_history_list){
        		if(this.operation_history_list.length){
                	for(var i in this.operation_history_list){
            			value_list.push([0, 0, this.operation_history_list[i]])
                	}
                }
        	}
            return value_list;
        },
        get_note_label: function(){
            return this.note_label;
        },
        get_note_label_display: function(){
        	var label = this.note_label;
        	if (label.length > 8)
        	      return label.substring(0,5) + '...';
        	   else
        	      return label;
        },
        set_note_label: function(note){
            this.note_label = note;
            this.trigger('change',this);
        },
        set_total_qty: function(){
    		var total_qty = 0;
    		var orderLines = this.get_orderlines();
            for (var i = 0; i < orderLines.length; i++) {
                var line = orderLines[i];
                if(!line.is_topping_line){
                	total_qty += line.quantity;
                }
            }
            this.total_qty = total_qty;
    	},
    	remove_orderline: function( line ){
            this.assert_editable();
            //Remove topping related
        	var orderlines = this.get_orderlines() 
        	var topping_line = orderlines.filter(function(tp_line) 
				{return tp_line.is_topping_line && tp_line.related_line_id == line.id;}
    		);
    		if(topping_line.length){
    			for (var i=0; i < topping_line.length; i++){
    				this.orderlines.remove(topping_line[i]);
    			}
    		}
    		this.orderlines.remove(line);
            this.select_orderline(this.get_last_orderline());
        },
//        add_product: function(product, options){
//        	alert('ok');
//            var line = _super_order.add_product.call(this,product,options);
//            if(options.combo_id){
//                line.set_combo(options.combo_id);
//            }
//            return line;
//        },
		get_last_orderline: function(){
			var orderLines = this.get_orderlines();
			var selected = 0;
            for (var i = orderLines.length-1; i >= 0; i--) {
                var line = orderLines[i];
                if(!line.is_topping_line){
                	selected = i;
					break;
                }
            }
	        return this.orderlines.at(selected);
	    },
        log_history_permisson: function(type, permisson_id, reason=false, product_id=false){
        	var history_value = {
				'date_perform':(new Date).format('Y-m-d H:i:s'),
				'type': type,
				'pos_permisson_id':permisson_id,
				'reason': reason,
				'product_id':product_id,
			}
        	this.set_operation_history_list(history_value);
    	},
    	get_payment_by_employee: function(employee_id){
        	var self = this;
        	var order = this.pos.get_order();
        	var amount_total = order.get_total_with_tax();
            var amount = amount_total - order.get_total_paid();
            var gui_order = self.pos.chrome.gui;
            if(amount <= 0){
            	return gui_order.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Đơn hàng đã thanh toán đủ',
                })
            }
        	
			rpc.query({
                model: 'hr.employee',
                method: 'get_on_acount_amount',
                args: [employee_id.id],
            })
            .then(function (result_from_server) {
                var on_acc_amount = result_from_server[0];
                var department = result_from_server[1]
				if (!result_from_server || on_acc_amount <= 0){
					return gui_order.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Ví tiền đã được sử dụng hết. Vui lòng kiểm tra lại',
	                })
				}else{
                    var amount_to_paid = (amount > on_acc_amount) ? on_acc_amount : amount;
                    var on_acc_balance = (amount > on_acc_amount) ? 0 : (on_acc_amount - amount);
//                    var on_acc_info = employee_id.name + ' - ' + department;
					var on_acc_info = employee_id.name
					order.add_paymentline(self.employee_cashregister);
	    			order.selected_paymentline.set_amount(amount_to_paid);
	    			order.selected_paymentline.set_max_on_account_amount(on_acc_amount);
                    order.selected_paymentline.set_employee_id(employee_id.id);
					order.selected_paymentline.employee_info = on_acc_info;
//                    order.selected_paymentline.set_on_account_info(on_acc_info);
	    			order.trigger('change', order);
					self.pos.chrome.screens.payment.show();
				}
            },function(error){
				error.event.preventDefault();
				gui_order.show_popup('error',{
	                'title': _t('Error: Could not Save Changes'),
	                'body': _t('Your Internet connection is probably down.'),
	            });
	        });
        },
		format_currency: function(amount,precision){
	        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
	        amount = parseInt(amount);
	        amount = this.format_currency_no_symbol(amount,precision);
	        if (currency.name == "VND"){
	        	amount = this.format_value(amount);
	        }
	        if (currency.position === 'after') {
	        	var a = amount + ' ' + (currency.symbol || '');
	            return a;
	        } else {
	            return (currency.symbol || '') + ' ' + amount;
	        }
	        
	    },
	    format_currency_no_symbol: function(amount, precision) {
	        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
	        var decimals = currency.decimals;
	
	        if (precision && (typeof this.pos.dp[precision]) !== undefined) {
	            decimals = this.pos.dp[precision];
	        }
	
	        this.format_currency_no_symbol = function(amount){
	            amount = round_pr(amount,currency.rounding);
	            if (typeof amount === 'number') {
		        	amount = round_di(amount,decimals).toFixed(decimals);
		        	if (currency.name == "VND"){
		        		amount = this.format_value(amount,0);
		        	}
		        }else{
		        	amount = amount.toFixed(decimals);
		        }
	            return amount;
	        };
	
	        if (typeof amount === 'number') {
	        	amount = round_di(amount,decimals).toFixed(decimals);
	        	if (currency.name == "VND"){
	        		amount = this.format_value(amount,0);
	        	}
	        }
	        return amount;
	    },
		check_order_payment_on_account: function(payment_type=false){
	    	var payment_lines = this.get_paymentlines();
			if(payment_lines.length){
				if(payment_type){
					var on_account_line = payment_lines.filter(function(line){
						return line.payment_method.use_for == payment_type;
					})
				}else{
					var on_account_line = payment_lines.filter(function(line){
						return line.payment_method.use_for=='on_account_emp' || line.payment_method.use_for=='on_account_customer';
					})
				}
				if(on_account_line.length){
					return true;
				}
			}
	    	return false;
	    	
	    },

		check_payment_on_account_by_partner_id: function(partner_id){
	    	var payment_lines = this.get_paymentlines();
			if(payment_lines.length){
				var on_account_line = payment_lines.filter(function(line){
					return line.payment_method.use_for == 'on_account_customer' && line.partner_id == partner_id;
				})
				if(on_account_line.length){
					return true;
				}
			}
	    	return false;
	    	
	    },
	
		remove_order_payment_on_account: function(){
			var self = this;
	    	var payment_lines = this.get_paymentlines();
			if(payment_lines.length){
				var on_account_line = payment_lines.filter(function(line){
					return line.payment_method.use_for=='on_account_emp' || line.payment_method.use_for=='on_account_customer';
				})
				_.each(on_account_line, function(l){
					self.remove_paymentline(l);
	                self.pos.chrome.screens.payment.reset_input();
	                self.pos.chrome.screens.payment.render_paymentlines();
				})
			}
	    	return false;
	    },

		check_payment_exceed_amount: function(){
			var self = this;
	    	var payment_lines = this.get_paymentlines();
			if(payment_lines.length){
				for (var i=0; i < payment_lines.length; i++){
    				var line = payment_lines[i];
					if(line.payment_method.use_for!='cash' && self.get_change(line)){
						return line;
					}
    			}
			}
	    	return false;
	    },

		reset_base_price_no_compute: function(apply_change){
			var self = this;
			var order = this.pos.get_order();
			var orderlines = self.orderlines;
			for (var i=0; i < orderlines.length; i++){
				var product = orderlines.models[i].product;
				var quantity = orderlines.models[i].quantity;
				var line = orderlines.models[i];
				if(apply_change){
					if (line.is_promotion_line || line.reward_id){
			 		    order.remove_orderline(line);
			 		    i -= 1;
		 		 	}else{
		 		 		if(product.lst_price != 0){
		 		 			line.remove_discount_line_no_render();
		 		 		}
		 		 	}
				}else{
					var rerender = false;
					self.get_base_price_by_line(product,quantity,line,apply_change,rerender);
					if(!line.old_price){
						line.set_old_price(product.list_price);
					}
				}
	      	}
		},
		//check order coupon line
		check_order_coupon_line: function(){
	    	var orderlines = this.get_orderlines();
	    	for (var i=0; i < orderlines.length; i++){
	    		if(orderlines[i].cup_type == 'themos' && orderlines[i].product_coupon_code){
	    			return false;
	    		}
	    	}
	    	return true;
	    	
	    },
    });
    
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this,attr,options);
            this.related_line_id = this.related_line_id || false;
            this.cup_type = this.cup_type || false;
            this.cup_type_default = this.cup_type_default || false;
            this.is_topping_line = this.is_topping_line || false;
            this.topping_name = this.topping_name || [];
            this.material_name = this.material_name || '';
			this.material_name_list = this.material_name_list || [];
            this.custom_material_list =  this.custom_material_list || [];
            this.disable_promotion = this.disable_promotion || false;
			this.cashless_code = this.cashless_code || false;
			this.product_coupon_code = this.product_coupon_code || '';
            this.promotion_available = false;
    	},
    	set_promotion_available: function(bool){
            this.promotion_available = bool;
            this.trigger('change',this);
        },
    	set_topping_name: function(name){
            this.topping_name = name;
            this.trigger('change',this);
        },
		get_topping_name: function(){
			var self = this
			var order = this.pos.get_order();
			if(this.topping_name.length){
				return this.topping_name;
			}
			var topping_list_name = [];
			var topping_line =  this.get_topping_list(true);
        	if(topping_line.length){
				for(var i in topping_line){
					var topping_name = topping_line[i].product.display_name;
//					var topping_x_qty = topping_line[i].quantity/self.quantity;
					if(topping_line[i].quantity != 1){
						topping_name = topping_name + ' (x' + topping_line[i].quantity.toString() + ')'
					}
//					var topping_price_fm = self.pos.get_order().format_currency_no_symbol(topping_line[i].get_display_price());
					var topping_price_fm = order.format_currency_no_symbol(order.get_new_price(topping_line[i].product, 1));
        			var topping_price_str = topping_price_fm.toString();
        			var name_with_price = topping_name + ' x ' + topping_price_str;
					topping_list_name.push(name_with_price);
				}
			}
			return topping_list_name;
		},
        set_cup_type: function(cup_type){
            this.cup_type = cup_type;
//            this.trigger('change',this);
        },
        set_cup_type_default: function(cup_type_default){
            this.cup_type_default = cup_type_default;
//            this.trigger('change',this);
        },
        set_material_name: function(name_list){
			this.material_name_list = name_list;
            this.material_name = name_list.join(', ');;
//            this.trigger('change',this);
        },
        set_custom_material_list: function(list){
            this.custom_material_list = list;
//            this.trigger('change',this);
        },
        set_disable_promotion: function(bool){
        	this.disable_promotion = bool;
        	this.trigger('change',this);
        },
        set_disable_loyalty: function(bool){
			var self = this;
        	this.disable_loyalty = bool;
			var orderlines = this.pos.get_order().get_orderlines();
			var topping_line = orderlines.filter(function(line) 
				{return line.is_topping_line && line.related_line_id == self.id;}
    		);
    		if(topping_line.length){
    			for(var line in topping_line){
					topping_line[line].disable_loyalty = bool;
//					this.trigger('change',this);
    			}
    		}
        	this.trigger('change',this);
        },
        get_option_ids: function(){
        	var value_list = [];
            if(this.custom_material_list.length){
            	for(var i in this.custom_material_list){
//            		if(this.custom_material_list[i].option_type != 'none'){
        			value_list.push([0, 0, this.custom_material_list[i]])
//            		}
            	}
            }
            return value_list;
        },
        
        export_as_JSON: function(){
            var json = _super_orderline.export_as_JSON.call(this);
            json.related_line_id = this.related_line_id;
            json.cup_type = this.cup_type != 'none' ? this.cup_type : false;
            json.is_topping_line = this.is_topping_line;
            json.option_ids = this.get_option_ids();
            json.disable_promotion = this.disable_promotion;
			json.cashless_code = this.cashless_code;
			json.product_coupon_code = this.product_coupon_code;
            return json;
        },
        get_unit_display_price_w_topping: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines() 
            var main_price =  this.get_unit_price();
        	var topping_price = 0;
            var topping_line = orderlines.filter(function(line) 
				{return line.is_topping_line && line.related_line_id == self.id;}
    		);
    		if(topping_line.length){
    			for(var line in topping_line){
    				topping_price += topping_line[line].get_unit_price()*topping_line[line].quantity/self.quantity;
    			}
    		}
    		var price_total = main_price + topping_price;
    		return price_total
        },
        get_display_price_w_topping: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines() 
            var main_price =  this.get_base_price();
        	var topping_price = 0;
            var topping_line = orderlines.filter(function(line) 
				{return line.is_topping_line && line.related_line_id == self.id;}
    		);
    		if(topping_line.length){
    			for(var line in topping_line){
    				topping_price += topping_line[line].get_base_price();
    			}
    		}
    		var price_total = main_price + topping_price;
    		return price_total;
        },
        set_quantity: function(quantity, keep_price){
        	var self = this;
			var old_qty = self.quantity;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines() 
    		_super_orderline.set_quantity.call(this,quantity, keep_price);
			var topping_line = orderlines.filter(function(line) 
				{return line.is_topping_line && line.related_line_id == self.id;}
    		);
    		if(topping_line.length){
    			for(var line in topping_line){
    				var current_qty = topping_line[line].quantity/old_qty;
    	        	current_qty = current_qty*quantity;
    				topping_line[line].set_quantity(current_qty, true);
    			}
    		}
			//Vuong: Always get integer quantity
			this.quantity = parseInt(this.quantity);
        },
		set_quantity_no_compute: function(quantity){
        	var self = this;
			var old_qty = self.quantity;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines() 
    		_super_orderline.set_quantity_no_compute.call(this,quantity);
			var topping_line = orderlines.filter(function(line) 
				{return line.is_topping_line && line.related_line_id == self.id;}
    		);
    		if(topping_line.length){
    			for(var line in topping_line){
    				var current_qty = topping_line[line].quantity/old_qty;
    	        	current_qty = current_qty*quantity;
    				topping_line[line].set_quantity(current_qty, true);
    			}
    		}
			//Vuong: Always get integer quantity
			this.quantity = parseInt(this.quantity);
        },
        get_quantity_str: function(){
            var quant = parseInt(this.quantity) || 0;
            return quant;
        },
    });
    
    var _super_payment_line = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
    	initialize: function(attr, options) {
    		_super_payment_line.initialize.call(this,attr,options);
    		this.max_on_account_amount = this.max_on_account_amount || 0;
            this.employee_id = this.employee_id || false;
			this.partner_id = this.partner_id || false;
            this.on_account_info = this.on_account_info || '';
    	},
    	init_from_JSON: function(json){
    		_super_payment_line.init_from_JSON.apply(this,arguments);
        	this.max_on_account_amount = json.max_on_account_amount || 0;
            this.employee_id = json.employee_id || false;
			this.partner_id = json.partner_id || false;
            this.on_account_info = json.on_account_info || '';
        },
        export_as_JSON: function(){
        	var json = _super_payment_line.export_as_JSON.call(this);
        	json.max_on_account_amount = this.max_on_account_amount || 0;
            json.employee_id = this.employee_id || false;
			json.partner_id = this.partner_id || false;
            json.on_account_info = this.on_account_info || '';
            return json;
        },
        set_max_on_account_amount: function(amount){
            this.max_on_account_amount = amount;
            this.trigger('change',this);
        },
        set_employee_id: function(employee_id){
            this.employee_id = employee_id;
            this.trigger('change',this);
        },
		set_partner_id: function(partner_id){
            this.partner_id = partner_id;
            this.trigger('change',this);
        },
        set_on_account_info: function(vals){
            this.on_account_info = vals;
            this.trigger('change',this);
        },
    	
    });
    
});

