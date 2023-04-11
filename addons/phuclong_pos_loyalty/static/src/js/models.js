odoo.define('phuclong_pos_loyalty.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var BarcodeReader = require('point_of_sale.BarcodeReader');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var _t = core._t;
    var gui = require('point_of_sale.gui');
    models.load_fields('res.partner',['appear_code_id','change_date_level', 'expired_date','ward_id',
									  'district_id','pos_note','use_for_on_account','wallet_on_account', 'active']);
	models.load_fields('loyalty.program', ['multiply_point_loyalty','sale_type_ids','categories_dom']);
	models.load_fields('loyalty.level', 'effective_time');
    
    models.load_models([
        {
        	model: 'cardcode.info',
            fields: ['hidden_code', 'card_type', 'state', 'date_expired', 'write_date', 'date_created'],
            domain: function(self){
                return [
                    ['state', 'in', ['using','close']]
                ];
            },
            loaded: function(self,card_code_ids){
            	self.db.add_card_code(card_code_ids); 
            },
        },{
    		model: 'hr.employee',
    		fields: ['emp_card_id','barcode','name','is_pos_manager','warehouses_dom', 'use_for_employee_coupon'],
    	    loaded: function(self,employees){
    	    	self.employee_by_barcode = [];
    	    	self.employee_by_carcode_id = [];
    	    	self.employee_by_id = [];
    	    	for (var i=0;i<employees.length;i++){
    	    		self.employee_by_barcode[employees[i].barcode]= employees[i];
    	    		self.employee_by_id[employees[i].id] = employees[i];
    	    		if(employees[i].emp_card_id){
    	    			self.employee_by_carcode_id[employees[i].emp_card_id[0]]= employees[i];
    	    		}
    	    	}
    	    },
    	},{
            model: 'res.country.state',
            fields: ['id','name','district_ids'],
            domain: function(self){ return [['country_id.code', '=', 'VN']];},
            order:  _.map(['name'], function (name) { return {name: name}; }),
            loaded: function(self,states){
                self.db.add_states(states);
            },
        },{
            model: 'res.district',
            fields: ['id','name','ward_ids','state_id'],
            domain: function(self){ return [['state_id.country_id.code', '=', 'VN']];},
            order:  _.map(['name'], function (name) { return {name: name}; }),
            loaded: function(self,districts){
                self.db.add_districts(districts);
            },
        },{
            model: 'res.ward',
            fields: ['id','name','district_id'],
            domain: function(self){ return [['district_id.country_id.code', '=', 'VN']];},
            order:  _.map(['name'], function (name) { return {name: name}; }),
            loaded: function(self,wards){
                self.db.add_wards(wards);
            },
        },
    ]);
    
	var posmodel_super = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
		load_new_partners: function(){
	        var self = this;
			self.load_new_card_code();
	        return new Promise(function (resolve, reject) {
				debugger;
	            var fields = _.find(self.models, function(model){ return model.label === 'load_partners'; }).fields;
	            var domain = self.prepare_new_partners_domain();
	            rpc.query({
	                model: 'res.partner',
	                method: 'search_read',
	                args: [domain, fields],
					context: { active_test: false },
	            }, {
	                timeout: 3000,
	                shadow: true,
	            })
	            .then(function (partners) {
	                if (self.db.add_partners(partners)) {   // check if the partners we got were real updates
	                    resolve();
	                } else {
	                    reject();
	                }
	            }, function (type, err) { reject(); });
	        });
	    },
		prepare_new_cardcodes_domain: function(){
	        return [['write_date','>', this.db.get_partner_write_date()],['state', 'in', ['draft','using','close']]];
	    },
		load_new_card_code: function(){
	        var self = this;
	        return new Promise(function (resolve, reject) {
	            var fields = _.find(self.models, function(model){ return model.model === 'cardcode.info'; }).fields;
	            var domain = self.prepare_new_cardcodes_domain();
	            rpc.query({
	                model: 'cardcode.info',
	                method: 'search_read',
	                args: [domain, fields],
	            }, {
	                timeout: 3000,
	                shadow: true,
	            })
	            .then(function (cardcodes) {
	                if (self.db.add_card_code(cardcodes)) { 
	                    resolve();
	                } else {
	                    reject();
	                }
	            }, function (type, err) { reject(); });
	        });
	    },
		get_loyalty_program: function(){
			var loyalty = false;
			var loyalty_available = [];
			var order = this.get_order();
			if(this.loyalties.length){
				for (var i=0;i<this.loyalties.length;i++){
					if(order && order.sale_type_id && this.loyalties[i].sale_type_ids.length && !this.loyalties[i].sale_type_ids.includes(order.sale_type_id)){
		        		continue;
		        	}
					loyalty_available.push(this.loyalties[i])
				}
			}
			if(loyalty_available.length){
				loyalty = loyalty_available[loyalty_available.length-1];
			}
			return loyalty;
		},
	});


    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this,arguments);
            this.unset_check_scan();
			this.partner_expired_date = this.partner_expired_date || false;
			this.partner_insert_type = this.partner_insert_type || false;
        },
		export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
			var client = this.get_client();
            var partner_expired_date = false;
			if(client){
				partner_expired_date = client.expired_date;
	            var current_point_act = client.current_point_act + this.get_won_points();
	            var loyalty_level = this.get_loyalty_level_by_point(current_point_act);
	            if(loyalty_level && loyalty_level.effective_time){
	                 if(!client.loyalty_level_id || client.loyalty_level_id[0] != loyalty_level.id){
	                 	 var date = new Date;
						 partner_expired_date = (new Date(date.setMonth(date.getMonth()+loyalty_level.effective_time))).format('Y-m-d');
	                 }
	            }
			}
			json.partner_expired_date = partner_expired_date;
			json.partner_insert_type = this.partner_insert_type;
            return json;
        },
		get_partner_expired_date: function(){
			var client = this.get_client();
            var partner_expired_date = false;
			if(client){
				partner_expired_date = client.expired_date;
	            var current_point_act = client.current_point_act + this.get_won_points();
	            var loyalty_level = this.get_loyalty_level_by_point(current_point_act);
	            if(loyalty_level && loyalty_level.effective_time){
	                 if(!client.loyalty_level_id || client.loyalty_level_id[0] != loyalty_level.id){
	                 	 var date = new Date;
						 partner_expired_date = (new Date(date.setMonth(date.getMonth()+loyalty_level.effective_time))).format('Y-m-d');
	                 }
	            }
			}
            return partner_expired_date;
		},
		get_partner_cardcode_expired_date: function(partner=false){
			if(!partner){
				partner = this.get_client();
			}
            var partner_expired_date = false;
			if(partner){
				if((partner.card_code_pricelist_id || partner.use_for_on_account) && partner.appear_code_id){
					var partner_by_card_code = this.pos.db.card_code_by_id[partner.appear_code_id[0]] || false;
					partner_expired_date = partner_by_card_code.date_expired || false;
				}
			}
            return partner_expired_date;
		},
        init_from_JSON: function(json){
            _super_order.init_from_JSON.apply(this,arguments);
            this.partner_expired_date = json.partner_expired_date;
			this.partner_insert_type = json.partner_insert_type;
        },
        unset_check_scan: function(){
        	this.check_scan_card_customer = false;
            this.check_keyboard_customer = false;
			this.check_create_customer = false;
            this.check_scan_manual_discount = false;
            this.check_scan_open_cashbox = false;
            this.check_scan_employee_coupon = false;
            this.check_scan_employee_payment = false;
			this.check_scan_partner_payment = false;
			this.check_scan_change_cashier = false;
        },
        set_check_scan_card_customer: function(bool){
            this.check_scan_card_customer = bool;
            this.trigger('change',this);
        },
        set_check_keyboard_customer: function(bool){
            this.check_keyboard_customer = bool;
            this.trigger('change',this);
        },
		set_check_create_customer: function(bool){
            this.check_create_customer = bool;
            this.trigger('change',this);
        },
        set_check_scan_manual_discount: function(bool){
            this.check_scan_manual_discount = bool;
            this.trigger('change',this);
        },
        set_check_scan_open_cashbox: function(bool){
            this.check_scan_open_cashbox = bool;
            this.trigger('change',this);
        },
        set_check_scan_employee_coupon: function(bool){
            this.check_scan_employee_coupon = bool;
            this.trigger('change',this);
        },
        set_check_scan_employee_payment: function(bool){
            this.check_scan_employee_payment = bool;
            this.trigger('change',this);
        },
		set_check_scan_partner_payment: function(bool){
            this.check_scan_partner_payment = bool;
            this.trigger('change',this);
        },
		set_check_scan_change_cashier: function(bool){
            this.check_scan_change_cashier = bool;
            this.trigger('change',this);
        },
        get_special_card_code: function(code){
        	if(code.includes(';')){
        		code = code.split(";").pop();
        	}
			var lastChar = code[code.length - 1];
    		if(lastChar == '?'){
    			code = code.slice(0,-1);
    		}
        	return code;
        },
		check_reward_loyalty_using: function(partner_id){
			var self = this;
			var gui_order = self.pos.chrome.gui;
			var expired_date = '';
			var warning = '';
			var partner_level = partner_id.loyalty_level_id ? this.get_loyalty_level_name_by_id(partner_id.loyalty_level_id[0]) : '';
			if((partner_id.card_code_pricelist_id || partner_id.use_for_on_account) && partner_id.appear_code_id){
				var partner_by_card_code = this.pos.db.card_code_by_id[partner_id.appear_code_id[0]] || false;
				expired_date = partner_by_card_code && partner_by_card_code.date_expired ? this.pos.get_format_date(partner_by_card_code.date_expired) : '';
				warning = [partner_id.name, 'Ngày hết hạn: ' + expired_date];
			}else{
				expired_date = partner_id.expired_date ? '(' + this.pos.get_format_date(partner_id.expired_date) + ')' : '';
				warning = [partner_id.name, 'Hạng thẻ ' + expired_date + ': ' + partner_level ];
			}
			
			rpc.query({
                model: 'pos.order',
                method: 'check_reward_loyalty_using',
                args: [partner_id.id],
            })
            .then(function (result_from_server) {
            	var result_from_server = result_from_server;
				if (!result_from_server.length){
					return gui_order.show_popup('alert',{
	                    'title': 'Thông báo',
	                    'body':  warning,
	                });
				}else{
					if(result_from_server[2] == 'reward'){
						warning =  warning.concat(['Bạn đã đổi quà tại cửa hàng',
							  result_from_server[0],
							  'Lúc: ' + result_from_server[1]])
					}else{
						warning =  warning.concat(['KH đã sử dụng dịch vụ E-office tại CH',
							  result_from_server[0],
							  'Lúc: ' + result_from_server[1]])
					}
					return gui_order.show_popup('alert',{
	                    'title': 'Thông báo',
	                    'body':  warning,
	                })
				}
            },function(error){
				error.event.preventDefault();
				return gui_order.show_popup('alert',{
                    'title': 'Thông báo',
                    'body':  warning,
                });
	        });
		},
        set_customer_by_code: function(code){
        	var self = this;
        	code = this.get_special_card_code(code);
        	var gui_order = self.pos.chrome.gui;
        	this.set_check_scan_card_customer(false);
//			gui_order.chrome.screens.clientlist.reload_partners();
        	var card_code = this.pos.db.card_code_by_barcode[code] || false;
        	if(!card_code){
        		return gui_order.show_popup('error',{'body':'Mã thẻ khách hàng không tồn tại'});
        	}else{
        		if(card_code.state!='using'){
        			var error = 'Thẻ khách hàng đã bị khoá';
//        			if(card_code.date_expired){
//        				error = error + ' vào ngày ' + this.pos.get_format_date(card_code.date_expired);
//        			}
        			return gui_order.show_popup('error',{'body': error});
        		}
        		if(card_code.card_type!='partner'){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ nhân viên không dùng để nhập khách hàng'});
        		}
        		var partner_by_card_code = this.pos.db.partner_by_card_code_id[card_code.id] || false;
        		if(!partner_by_card_code){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ không gắn với khách hàng nào'});
        		}else{
					if(partner_by_card_code.card_code_pricelist_id && (!card_code.date_expired || !card_code.date_created)){
						return gui_order.show_popup('error',{'body':'Mã thẻ khách hàng không tồn tại'});
					}
					if(!partner_by_card_code.active){
						return gui_order.show_popup('error',{'body':'Thông tin khách hàng liên kết với thẻ đã bị lưu trữ'});
					}
					if(partner_by_card_code.expired_date && !partner_by_card_code.card_code_pricelist_id && !partner_by_card_code.use_for_on_account){
						var now_date = new Date;
						now_date.setHours(0,0,0,0);
						var expired_date = new Date(partner_by_card_code.expired_date);
						expired_date.setHours(0,0,0,0);
						if(expired_date < now_date){
							return gui_order.show_popup('error',{'body': 'Loyalty của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
						}
					}
					if((partner_by_card_code.card_code_pricelist_id || partner_by_card_code.use_for_on_account) && card_code.date_expired){
						var now_date = new Date;
						now_date.setHours(0,0,0,0);
						var expired_date = new Date(card_code.date_expired);
						expired_date.setHours(0,0,0,0);
						if(expired_date < now_date){
							return gui_order.show_popup('error',{'body': 'Thẻ của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
						}
						if(!self.check_order_coupon_line()){
							return gui_order.show_popup('error',{'body': 'Không sử dụng thẻ này cho đơn hàng áp dụng Coupon trên sản phẩm'});
						}
					}
//					gui_order.chrome.screens.clientlist.reload_partners();
					self.partner_insert_type = 'scan';
					self.set_client(partner_by_card_code);
//					gui_order.chrome.screens.products.order_widget.update_summary();
//					gui_order.chrome.screens.products.order_widget.renderElement();
//        			if(gui_order.current_popup){
//        				gui_order.current_popup.click_confirm()
//        			}
//					return self.check_reward_loyalty_using(partner_by_card_code);
        		}
        	}
        },
		get_payment_by_partner: function(code){
        	var self = this;
        	code = this.get_special_card_code(code);
        	var gui_order = self.pos.chrome.gui;
        	this.set_check_scan_partner_payment(false);
        	var card_code = this.pos.db.card_code_by_barcode[code] || false;
        	if(!card_code){
        		return gui_order.show_popup('error',{'body':'Mã thẻ khách hàng không tồn tại'});
        	}else{
        		if(card_code.state!='using'){
        			var error = 'Thẻ khách hàng đã bị khoá';
//        			if(card_code.date_expired){
//        				error = error + ' vào ngày ' + this.pos.get_format_date(card_code.date_expired);
//        			}
        			return gui_order.show_popup('error',{'body': error});
        		}
        		if(card_code.card_type!='partner'){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ nhân viên không dùng để nhập khách hàng'});
        		}
				if(!card_code.date_expired){
					return gui_order.show_popup('error',{'body': 'Mã thẻ không hợp lệ vì chưa có ngày hết hạn'});
				}
        		var partner_by_card_code = this.pos.db.partner_by_card_code_id[card_code.id] || false;
        		if(!partner_by_card_code){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ không gắn với khách hàng nào'});
        		}else{
					if(partner_by_card_code.expired_date && !partner_by_card_code.card_code_pricelist_id && !partner_by_card_code.use_for_on_account){
						var now_date = new Date;
						now_date.setHours(0,0,0,0);
						var expired_date = new Date(partner_by_card_code.expired_date);
						expired_date.setHours(0,0,0,0);
						if(expired_date < now_date){
							return gui_order.show_popup('error',{'body': 'Loyalty của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
						}
					}
					if((partner_by_card_code.card_code_pricelist_id || partner_by_card_code.use_for_on_account) && card_code.date_expired){
						var now_date = new Date;
						now_date.setHours(0,0,0,0);
						var expired_date = new Date(card_code.date_expired);
						expired_date.setHours(0,0,0,0);
						if(expired_date < now_date){
							return gui_order.show_popup('error',{'body': 'Thẻ của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
						}
					}
					if(this.check_payment_on_account_by_partner_id(partner_by_card_code.id)){
						return gui_order.show_popup('alert',{
		                    'title': 'Cảnh báo',
		                    'body':  'Thẻ trả trước này đã được sử dụng, vui lòng xóa dòng thanh toán và nhập lại',
		                })
					}
        			if(gui_order.current_popup){
        				gui_order.current_popup.click_confirm()
        			}
					return self.set_payment_on_account_partner(partner_by_card_code);
        		}
        	}
        },
		set_payment_on_account_partner: function(partner_id){
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
                model: 'res.partner',
                method: 'get_on_acount_amount',
                args: [partner_id.id],
            })
            .then(function (result_from_server) {
                var on_acc_amount = result_from_server;
				if (!result_from_server || on_acc_amount <= 0){
					return gui_order.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Ví tiền đã được sử dụng hết. Vui lòng kiểm tra lại',
	                })
				}else{
                    var amount_to_paid = (amount > on_acc_amount) ? on_acc_amount : amount;
                    var on_acc_balance = (amount > on_acc_amount) ? 0 : (on_acc_amount - amount);
                    var on_acc_info = partner_id.name;
					order.add_paymentline(self.partner_cashregister);
	    			order.selected_paymentline.set_amount(amount_to_paid);
	    			order.selected_paymentline.set_max_on_account_amount(on_acc_amount);
                    order.selected_paymentline.set_partner_id(partner_id.id);
					order.selected_paymentline.partner_info = on_acc_info;
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
        check_employee_code: function(code, pos_manager=true){
        	var self = this;
        	code = this.get_special_card_code(code);
        	var gui_order = self.pos.chrome.gui;
        	this.unset_check_scan();
        	var card_code = this.pos.db.card_code_by_barcode[code] || false;
        	if(!card_code){
        		return gui_order.show_popup('error',{'body':'Mã thẻ nhân viên không tồn tại'});
        	}else{
        		if(card_code.state!='using'){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ không được kích hoạt'});
        		}
        		if(card_code.card_type=='partner'){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ khách hàng không dùng để nhập nhân viên'});
        		}
        		
        		var emp_by_card_code = this.pos.employee_by_carcode_id[card_code.id] || false;
        		if(!emp_by_card_code){
        			return gui_order.show_popup('error',{'body': 'Mã thẻ không gắn với nhân viên nào'});
        		}else{
        			if(pos_manager){
            			if(!emp_by_card_code.is_pos_manager){
            				return gui_order.show_popup('error',{'body': 'Nhân viên không phải là cửa hàng trưởng'});
            			}
            			var warehouse_allowed = JSON.parse(emp_by_card_code.warehouses_dom);
        				if (warehouse_allowed.length && !warehouse_allowed.includes(self.pos.config.warehouse_id[0])){
        					return gui_order.show_popup('error',{'body': 'Cửa hàng trưởng không có quyền ở cửa hàng này'});
        				}
            		}
        			return emp_by_card_code.id;
        		}
        		
        	}
        },
//		get_won_points: function(){
//			var total_points = _super_order.get_won_points.apply(this,arguments);
//			var multiply_point_loyalty = this.pos.get_loyalty_program().multiply_point_loyalty;
//	        if(total_points !=0 && !this.multiply_point && multiply_point_loyalty){
//	        	total_points*= multiply_point_loyalty;
//	        }
//	        return total_points;
//	    },
		get_won_points: function(){
	        if (!this.pos.get_loyalty_program() || !this.get_client() || !this.check_condition_loyalty_order()) {
	            return 0;
	        }
	        if(this.get_client().mobile === '0000000000'){
	        	return 0;
	        }
	        var orderLines = this.get_orderlines();
	        var rounding   = this.pos.get_loyalty_program().rounding;
	        var rounding_method = this.pos.get_loyalty_program().rounding_method;
	        
	        var product_sold = 0;
	        var total_sold = 0;
			var total_sold_multipoint = 0;
	        var total_points = 0;
			var multiply_point_loyalty = this.pos.get_loyalty_program().multiply_point_loyalty;
			
	        for (var i = 0; i < orderLines.length; i++) {
	            var line = orderLines[i];
	            var product = line.get_product();
	            var rules  = this.pos.get_loyalty_program().rules_by_product_id[product.id] || [];
	            var overriden = false;
	
	            if (line.get_reward()) {  // Reward products are ignored
	                continue;
	            }
	            if(line.promotion_id || line.promotion_condition_id || line.promotion_all_order_id){
					continue;
				}
	            if (!line.check_condition_loyalty()) {  
	                continue;
	            }
	            
	            for (var j = 0; j < rules.length; j++) {
	                var rule = rules[j];
	                total_points += this.round_precision(line.get_quantity() * rule.pp_product, rounding, rounding_method);
	                if(rule.pp_currency!=0){
	                	total_points += this.round_precision(line.get_price_with_tax() / rule.pp_currency, rounding, rounding_method);
	                }
	                // if affected by a non cumulative rule, skip the others. (non cumulative rules are put
	                // at the beginning of the list when they are loaded )
	                if (!rule.cumulative) { 
	                    overriden = true;
	                    break;
	                }
	            }
	
	            // Test the category rules
	            if ( product.pos_categ_id ) {
	                var category = this.pos.db.get_category_by_id(product.pos_categ_id[0]);
	                while (category && !overriden) {
	                    var rules = this.pos.get_loyalty_program().rules_by_category_id[category.id] || [];
	                    for (var j = 0; j < rules.length; j++) {
	                        var rule = rules[j];
	                        total_points += this.round_precision(line.get_quantity() * rule.pp_product, rounding, rounding_method);
	                        if(rule.pp_currency!=0){
	                        	total_points += this.round_precision(line.get_price_with_tax() / rule.pp_currency, rounding, rounding_method);
	                        }
	                        if (!rule.cumulative) {
	                            overriden = true;
	                            break;
	                        }
	                    }
	                    var _category = category;
	                    category = this.pos.db.get_category_by_id(this.pos.db.get_category_parent_id(category.id));
	                    if (_category === category) {
	                        break;
	                    }
	                }
	            }
	
	            if (!overriden) {
	                product_sold += line.get_quantity();
					var point_per_line = line.get_price_with_tax();
					var categories_dom = this.pos.get_loyalty_program().categories_dom;
			        if(point_per_line && multiply_point_loyalty && (!categories_dom || categories_dom.includes(product.categ_id[0]))){
//			        	point_per_line*= multiply_point_loyalty;
						total_sold_multipoint += point_per_line;
			        }else{
						total_sold += point_per_line;
					}
	            }
	        }

	        if(this.discount_amount && (total_sold + this.discount_amount >= 0)){
	        	total_sold += this.discount_amount;
	        }
	        if(this.pos.get_loyalty_program().pp_currency!=0){
	        	total_points += this.round_precision( total_sold / this.pos.get_loyalty_program().pp_currency, rounding, rounding_method);
				if(total_sold_multipoint){
					total_points += multiply_point_loyalty*this.round_precision( total_sold_multipoint / this.pos.get_loyalty_program().pp_currency, rounding, rounding_method);
				}
	        }
	        total_points += this.round_precision( product_sold * this.pos.get_loyalty_program().pp_product, rounding, rounding_method);
	        total_points += this.round_precision( this.pos.get_loyalty_program().pp_order, rounding, rounding_method);
	        
	        if(this.multiply_point !=0){
	        	total_points*= this.multiply_point;
	        }
	        return total_points;
	    },
		check_condition_loyalty_order: function(){
			var self = this;
			var orderlines = this.get_orderlines();
			if(this.check_order_payment_voucher() || this.check_order_payment_on_account()){
				return false;
			}
			//pricelist by cardcode
			var partner = self.get_client();
			if(partner && (partner.card_code_pricelist_id || partner.use_for_on_account)){
				return false;
			}
			var total_promotion_line = orderlines.filter(function(l){
				if(l.is_promotion_line && l.promotion_line_id && self.pos.promotion_lines[l.promotion_line_id][0].product_attribute == 'order'){
					return true;
				}
				return l.promotion_all_order_id;
			})
			if(total_promotion_line.length){
				return false;
			}
			return true;
		},
		
		finalize: function(){
	        var client = this.get_client();
	        if ( client ) {
	            client.expired_date = this.get_partner_expired_date();
	            this.pos.gui.screen_instances.clientlist.partner_cache.clear_node(client.id);
	        }
	        _super_order.finalize.apply(this,arguments);
	    },

		remove_loyalty_discount:function (orderline=false){
			_super_order.remove_loyalty_discount.apply(this,arguments);
			var orderlines = this.get_orderlines();
			if(orderline){
				var topping_line = orderlines.filter(function(line) 
					{return line.is_topping_line && line.related_line_id == orderline.id;}
	    		);
	    		if(topping_line.length){
	    			for(var line in topping_line){
						topping_line[line].is_loyalty_line = false;
						topping_line[line].set_loyalty_discount(0);
	    			}
	    		}
			}
			this.trigger('change',this);
		},
		
		set_client: function(client, check_promotion=false){
			var self = this;
	        this.assert_editable();
			var old_client = this.get_client();
			var gui_order = self.pos.chrome.gui;
			if(client && client.card_code_pricelist_id){
				if(!check_promotion){
					return gui_order.show_popup('confirm',{
	        			'title':  'Cảnh báo',
	                    'body':  'Đơn hàng sử dụng thẻ này sẽ áp dụng bảng giá riêng và không áp dụng chung với CTKM',
						'confirm': function() {
							self.set_client(client, true)
						}
					})
				}else{
					this.set('client',client);
					this.remove_loyalty_discount();
					this.reset_base_price(true);
	                this.remove_current_discount();
	                this.unset_promotion_for_coupon();
					this.remove_combo_done();
					this.checked_loyalty_level = false;
		            this.set_unchecked_disc_loyalty();
		    		this.set_unchecked_disc_birthdate();
					this.get_new_price_all_line();
					if(client){
						self.check_reward_loyalty_using(client);
					}
					gui_order.chrome.screens.products.order_widget.update_summary();
					gui_order.chrome.screens.products.order_widget.renderElement();
				}
				
			}else{
				this.set('client',client);
				this.remove_loyalty_discount();
				if(old_client && old_client.card_code_pricelist_id){
					this.reset_base_price(true);
	                this.remove_current_discount();
				}
				this.checked_loyalty_level = false;
	            this.set_unchecked_disc_loyalty();
	    		this.set_unchecked_disc_birthdate();
//				this.compute_promotion();
				if(client){
					self.check_reward_loyalty_using(client);
				}
				gui_order.chrome.screens.products.order_widget.update_summary();
				gui_order.chrome.screens.products.order_widget.renderElement();
			}
	    },
		check_product_loyalty_gift: function(product_tmpl){
			if(this.pos.db.check_is_locked(product_tmpl.id)){
				return false;
			}
			return true;
		}
		
    });
    
    screens.ClientListScreenWidget.include({
		save_changes: function(){
			var self = this;
			var order = this.pos.get_order();
			if( this.has_client_changed() && this.new_client){
				if(this.pos.config.is_callcenter_pos){
					var partner = this.new_client;
					var note = partner.address
					if(partner.pos_note){
						note += ' - ' + partner.pos_note;
					}
					order.note_address = note;
					order.note_mobile = partner.mobile;
	            	if(note){
	            		note = partner.mobile + ' - ' + note;
	            	}else{
	            		note = partner.mobile;
	            	}
	            	order.set_note(note);
					return;
				}else{
					return this.gui.show_popup('error', 'Khách hàng chưa gắn mã thẻ, vui lòng kiểm tra lại');
				}
			}
			self._super()
		},
		confirm_save_client_details: function(partner) {
			var self = this;
			var fields = {};
	        this.$('.client-details-contents .detail').each(function(idx,el){
	            fields[el.name] = el.value || false;
	        });
	
	        if (!fields.name) {
	            this.gui.show_popup('error', 'Tên khách hàng là thông tin bắt buộc');
	            return;
	        }
	        
	        if (!fields.mobile) {
	            this.gui.show_popup('error', 'Số di động là thông tin bắt buộc');
	            return;
	        }

			if (!fields.pos_note) {
	            this.gui.show_popup('error', 'Ghi chú mã thẻ nổi là thông tin bắt buộc');
	            return;
	        }

			if (fields.birthday) {
	            var date_of_birth = fields.birthday;
	            var year = 2000;
	            date_of_birth = date_of_birth.replace(/[&\/\\#,+()$~%.'":*?<>{}]/g,'');
	            if(fields.birthday.length != 10 ||  fields.birthday[2] != '/' || fields.birthday[5] != '/' || date_of_birth.length != 8){
	            	this.gui.show_popup('error', 'Vui lòng nhập ngày tháng theo đúng định dạng dd/mm/yyyy');
	                return;
	            }
	        }

			if (fields.email && !fields.email.includes('@')) {
            	this.gui.show_popup('error', 'Email phải đúng định dạng: tên_email@ (ví dụ: nhan.nghia@gmail.com)');
                return;
	        }

			rpc.query({
                model: 'res.partner',
                method: 'check_create_from_ui',
                args: [fields],
            })
            .then(function(result){
				if(result != true){
					return self.gui.show_popup('error',result);
				}
                self.gui.show_popup('confirm',{
		            'title': 'Cảnh báo',
		            'body': 'Bạn có chắc thông tin đã được nhập chính xác và đầy đủ?',
		            confirm: function(){
		            	self.save_client_details(partner);
		            },
		        });
            }).catch(function(error){
                error.event.preventDefault();
                var error_body = _t('Your Internet connection is probably down.');
                if (error.message.data) {
                    var except = error.message.data;
                    error_body = except.arguments && except.arguments[0] || except.message || error_body;
                }
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': error_body,
                });
            });
		},
		save_client_details: function(partner) {
	        var self = this;
	        
	        var fields = {};
	        this.$('.client-details-contents .detail').each(function(idx,el){
	            fields[el.name] = el.value || false;
	        });
	
	        if (!fields.name) {
	            this.gui.show_popup('error', 'Tên khách hàng là thông tin bắt buộc');
	            return;
	        }
	        
	        if (!fields.mobile) {
	            this.gui.show_popup('error', 'Số di động là thông tin bắt buộc');
	            return;
	        }

			if (!fields.pos_note) {
	            this.gui.show_popup('error', 'Ghi chú mã thẻ nổi là thông tin bắt buộc');
	            return;
	        }
	        
	        if (fields.birthday) {
	            var date_of_birth = fields.birthday;
	            var year = 2000;
				date_of_birth = date_of_birth.replace(/[&\/\\#,+()$~%.'":*?<>{}]/g,'');
	            if(fields.birthday.length != 10 ||  fields.birthday[2] != '/' || fields.birthday[5] != '/' || date_of_birth.length != 8){
	            	this.gui.show_popup('error', 'Vui lòng nhập ngày tháng theo đúng định dạng dd/mm/yyyy');
	                return;
	            }
	            var date = parseInt(date_of_birth.slice(0, 2));
				var month = parseInt(date_of_birth.slice(2, 4))-1;
				if(date_of_birth.length == 8){
					year = parseInt(date_of_birth.slice(4, 8));
				}
				var date = new Date(year, month, date);
				var date_format = date.format("Y-m-d");
				fields.birthday = date_format;
	        }
	        
	        if (this.uploaded_picture) {
	            fields.image = this.uploaded_picture;
	        }
	
	        fields.id           = partner.id || false;
	        fields.country_id   = fields.country_id && parseInt(fields.country_id) || false;
			fields.state_id   = fields.state_id && parseInt(fields.state_id) || false;
			fields.district_id   = fields.district_id && parseInt(fields.district_id) || false;
			fields.ward_id   = fields.ward_id && parseInt(fields.ward_id) || false;
	
	        if (fields.property_product_pricelist) {
	            fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
	        } else {
	            fields.property_product_pricelist = false;
	        }
	
	        rpc.query({
                model: 'res.partner',
                method: 'create_from_ui',
                args: [fields],
            })
            .then(function(partner_id){
                if ($.isNumeric(partner_id)==true){
            		self.saved_client_details(partner_id);
            	}
            	else{
            		self.gui.show_popup('error',_t(partner_id));
            	}
            }).catch(function(error){
                error.event.preventDefault();
                var error_body = _t('Your Internet connection is probably down.');
                if (error.message.data) {
                    var except = error.message.data;
                    error_body = except.arguments && except.arguments[0] || except.message || error_body;
                }
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': error_body,
                });
            });
	    },
		onchange_state_id: function(state_id){
            var res = this.pos.db.get_district_by_state(state_id);
            var select = this.$('.client-details-contents').find('select.onchange_district_id');
            select.children().remove().end().append(QWeb.render('partnerAddressDistrict',{widget:this,district_ids:res}));
            $(select.children()[0]).attr('selected','selected').trigger('change');
        },
        onchange_district_id: function(district_id){
            var res = this.pos.db.get_ward_by_district(district_id);
            var select = this.$('.client-details-contents').find('select.onchange_ward_id');
            select.children().remove().end().append(
                $(QWeb.render('partnerAddressWard',{widget:this,ward_ids:res}))
            );
            $(select.children()[0]).attr('selected','selected');
        },
		display_client_details: function(visibility,partner,clickpos){
            var self = this;
			var order = self.pos.get_order();
            var contents = this.$('.client-details-contents');
            contents.off('change','.onchange_state_id');
            contents.off('change','.onchange_district_id');
            contents.off('change','.onchange_ward_id'); 
            contents.on('change','.onchange_state_id',function(){
                self.onchange_state_id($(this).val());
            });
            contents.on('change','.onchange_district_id',function(){
                self.onchange_district_id($(this).val());
            });
            this._super(visibility,partner,clickpos);
//			if(visibility == 'show' && partner){
//				order.partner_insert_type = 'search';
//				if(self.pos.config.is_callcenter_pos){
//					var note = partner.address
//					if(partner.pos_note){
//						note += ' - ' + partner.pos_note;
//					}
//					order.note_address = note;
//					order.note_mobile = partner.mobile;
//	            	if(note){
//	            		note = partner.mobile + ' - ' + note;
//	            	}else{
//	            		note = partner.mobile;
//	            	}
//	            	order.set_note(note);
//				}
//			}
            this.$('.client-list-contents').empty();
			contents.off('click','.button.save'); 
			contents.on('click','.button.save',function(){ self.confirm_save_client_details(partner); });
            
        },
        render_list: function(partners){
            var search = this.$('.searchbox input').val();
            if(search.length == 0){
                this.$('.client-list-contents').empty();
                
            } else{
                this._super(partners.slice(0,5));
            }
        },
        show: function(){
            var self = this;
			this._super();
			var gui_order = self.pos.chrome.gui;
			var order = self.pos.get_order();
            this.$('.client-list-contents').off('click', '.client-line');
            this.$('.client-list-contents').on('click', '.client-line', function(event){
				var partner = self.pos.db.get_partner_by_id(parseInt($(this).data('id')));
				if(!partner.appear_code_id && !self.pos.config.is_callcenter_pos){
					return gui_order.show_popup('error',{'body':'Khách hàng chưa gắn mã thẻ, vui lòng kiểm tra lại'});
				}
				var card_code = partner.appear_code_id ? self.pos.db.card_code_by_id[partner.appear_code_id[0]] : false;
				if(partner.card_code_pricelist_id && card_code && (!card_code.date_expired || !card_code.date_created)){
					return gui_order.show_popup('error',{'body':'Mã thẻ khách hàng không tồn tại'});
				}
//				if(partner.use_for_on_account){
//					return gui_order.show_popup('error',{'body':'Mã thẻ này không dùng để tích điểm Loyalty'});
//				}
//				if(partner.expired_date){
//					var now_date = new Date;
//					now_date.setHours(0,0,0,0);
//					var expired_date = new Date(partner.expired_date);
//					expired_date.setHours(0,0,0,0);
//					if(expired_date < now_date){
//						return self.gui.show_popup('error',{'body': 'Loyalty của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
//					}
//				}
				if(partner.expired_date && !partner.card_code_pricelist_id && !partner.use_for_on_account){
					var now_date = new Date;
					now_date.setHours(0,0,0,0);
					var expired_date = new Date(partner.expired_date);
					expired_date.setHours(0,0,0,0);
					if(expired_date < now_date){
						return gui_order.show_popup('error',{'body': 'Loyalty của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
					}
				}
				if((partner.card_code_pricelist_id || partner.use_for_on_account) && card_code && card_code.date_expired){
					var now_date = new Date;
					now_date.setHours(0,0,0,0);
					var expired_date = new Date(card_code.date_expired);
					expired_date.setHours(0,0,0,0);
					if(expired_date < now_date){
						return gui_order.show_popup('error',{'body': 'Thẻ của khách hàng đã hết hạn vào ngày ' + expired_date.format('d-m-Y')});
					}
					if(!order.check_order_coupon_line()){
						return gui_order.show_popup('error',{'body': 'Không sử dụng thẻ này cho đơn hàng áp dụng Coupon trên sản phẩm'});
					}
				}
//                self.line_select(event,$(this),parseInt($(this).data('id')));
				self.gui.back();
				order.partner_insert_type = 'search';
				if(self.pos.config.is_callcenter_pos){
					var note = partner.address
					if(partner.pos_note){
						note += ' - ' + partner.pos_note;
					}
					order.note_address = note;
					order.note_mobile = partner.mobile;
	            	if(note){
	            		note = partner.mobile + ' - ' + note;
	            	}else{
	            		note = partner.mobile;
	            	}
	            	order.set_note(note);
					if(partner.appear_code_id){
						self.pos.get_order().set_client(partner);
					}
				}else{
					self.pos.get_order().set_client(partner);
				}
//				gui_order.chrome.screens.products.order_widget.update_summary();
//				gui_order.chrome.screens.products.order_widget.renderElement();
//				self.pos.get_order().check_reward_loyalty_using(partner);
            });
			
			this.$('.new-customer').off('click');
			this.$('.new-customer').click(function(){
				var order = self.pos.get_order();
				if(self.pos.config.is_callcenter_pos){
					self.display_client_details('edit',{
		                'country_id': self.pos.company.country_id,
	//	                'state_id': self.pos.company.state_id,
		            });
				}else{
					return self.gui.show_popup('confirm',{
			            'title': 'Cảnh báo',
			            'body': 'Bạn có chắc đơn hàng đủ điều kiện tạo khách hàng hay không ?',
			            confirm: function(){
			            	order.set_check_create_customer(true);
							self.gui.show_popup('cardscanner',{
			        	    	title: 'Xin hãy quẹt thẻ Quản lý cửa hàng vào máy quét'
			        	    });
			            },
			        });
				}
//	            self.display_client_details('edit',{
//	                'country_id': self.pos.company.country_id,
////	                'state_id': self.pos.company.state_id,
//	            });
	        });
			
			this.$('.back').off('click');
			this.$('.back').click(function(){
				if(self.editing_client){
					return self.gui.show_popup('confirm',{
			            'title': 'Cảnh báo',
			            'body': 'Thông tin khách hàng chưa hoàn thành, bạn có chắc muốn quay trở lại?',
			            confirm: function(){
			            	self.gui.back();
			            },
			        });
				}
	            self.gui.back();
	        });
        },
    });
    
});

