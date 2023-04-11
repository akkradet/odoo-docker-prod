odoo.define('phuclong_pos_promo_combo.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var QWeb     = core.qweb;
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    
    models.load_models([
        {
            model: 'sale.promo.combo',
            fields: [
                'id',
                'active',
                'combo_line_ids',
                'combo_price',
                'day_of_week',
                'display_name',
                'end_date',
                'end_hour',
                'name',
                'sale_type_ids',
                'start_date',
                'start_hour',
                'state',
                'sum_of_qty',
                'warehouse_ids',
                'use_for_coupon'
            ],
            domain: function(self){
                var now = moment().format('YYYY-MM-DD');
				return [
                    ['active','=',true],
                    ['state', '=', 'approved'],
                    '|',
                    ['start_date','=',false],
                    ['start_date','<=',now],
                    '|',
                    ['end_date','=',false],
                    ['end_date','>=',now]
                ];
            },
            loaded: function(self,combo_list){
                var combos = [];
                var warehouse_id = globalThis.posmodel.config.warehouse_id[0];  
                _.each(combo_list,function(combo){
                    if (combo.warehouse_ids.indexOf(warehouse_id) >= 0 || combo.warehouse_ids.length == 0){
                        combos.push(combo);
                    }
                });
                self.db.list_combo = combos;
            },
        },{
            model: 'sale.promo.combo.line',
            fields: [
                'display_name',
                'id',
                'name',
                'product_list_ids',
                'qty_combo',
                'sale_promo_combo_id',
                'sub_total',
                'unit_price_combo',
                'categories_dom',
				'use_pricelist'
            ],
            domain: function(self){
                return [
                    ['sale_promo_combo_id', 'in', self.db.list_combo.map(function (el) { return el.id; })],
                ];
            },
            loaded: function(self, combo_lines){
                self.db.combo_lines = combo_lines;
            },
        },{
            model: 'sale.promo.combo.line.detail',
            fields: [
                'product_id',
                'sale_promo_combo_line_id',
				'sub_price',
                'unit_price_combo',
            ],
            domain: function(self){
                return [
                    ['sale_promo_combo_line_id', 'in', self.db.combo_lines.map(function (el) { return el.id; })],
                ];
            },
            loaded: function(self, combo_lines_detail){
                self.db.combo_lines_detail = combo_lines_detail;
            },
        }

    ]);
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this,attr,options);
            this.combo_id =  options.combo_id || false;
            this.combo_qty =  this.combo_qty || 0;
            this.is_done_combo =  this.is_done_combo || false;
            this.combo_line_id = this.combo_line_id || false;
            this.combo_seq = this.combo_seq || false;
            this.combo_coupon_code = this.combo_coupon_code || false;
        },
        export_as_JSON: function(){
            var json = _super_orderline.export_as_JSON.call(this);
            json.combo_id = this.combo_id;
            json.combo_qty = this.combo_qty;
            json.is_done_combo =  this.is_done_combo;
            json.combo_line_id = this.combo_line_id;
            json.combo_seq = this.combo_seq || false;
            return json;
        },
        init_from_JSON: function(json){
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.combo_id = json.combo_id;
            this.combo_qty = json.combo_qty;
            this.is_done_combo =  json.is_done_combo;
            this.combo_line_id = json.combo_line_id;
            this.combo_seq = json.combo_seq || false;
        },
        set_combo: function(combo){
            this.combo_id = combo.id;
        },
        set_combo_line: function(combo_line){
            this.combo_line_id = combo_line.id;
        },
        set_combo_qty: function(qty){
            this.combo_qty = qty;
        },
        set_is_done_combo: function(val){
            this.is_done_combo = val;
        },
        set_combo_seq: function(val){
            this.combo_seq = val;
        },
        set_combo_coupon_code: function(code){
        	this.combo_coupon_code = code;
        	this.trigger('change',this);
        }
    });
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
    	initialize: function() {
            _super_order.initialize.apply(this,arguments);
            this.combo_coupon_id = this.combo_coupon_id || false;
            this.combo_coupon_code = this.combo_coupon_code || false;
        },
        set_combo_coupon: function(combo_coupon_id, code=false){
            this.combo_coupon_id = combo_coupon_id;
            this.combo_coupon_code = code;
            this.trigger('change',this);
        },
        check_condition_discount_line: function(orderline){
            var res = _super_order.check_condition_discount_line.apply(this,arguments);
            // Thái: Khi đang ở màn hình chọn Combo thì không tính promotion
            if(orderline.combo_id || this.pos.chrome.screens.products.product_categories_widget.combo){
                return false;
            }
            //Vuong: disable by tool choose promotion
//            if(orderline.disable_promotion || this.has_printed_label_first || orderline.is_topping_line){
			if(orderline.disable_promotion || this.linked_draft_order_be || (orderline.cup_type == 'themos' && orderline.product_coupon_code)){
                return false;
            }
            return res;
        },
        add_product: function(product, options){
            var line = _super_order.add_product.call(this,product,options);
            if(options && options.combo_id){
                line.set_combo(options.combo_id);
            }
            return line;
        },
        compute_combo: function(){
            var self = this;
            var order_lines = this.orderlines;
            var list_combo = this.pos.db.list_combo;
            var return_true = true;
            var line_in_combo = order_lines.filter(function(item){return item.is_done_combo});
            if (line_in_combo.length>0){
                var combo_seq = Math.max.apply(Math, line_in_combo.map(function(o) { return o.combo_seq; })) + 1;
            } else{
                var combo_seq =1;
            }
            // Lặp theo từng combo
            _.each(list_combo,function(combo){
                var total_combo_qty = 0;
                var order_line_for_this_combo = order_lines.filter(function(line){return line.is_done_combo == false && line.combo_id && line.combo_id == combo.id})
                var combo_line_to_compute = self.pos.db.combo_lines.filter(function(item){return item.sale_promo_combo_id[0] == combo.id});
				//set waiting_combo_line
				_.each(combo_line_to_compute, function(line){
                    total_combo_qty += line.qty_combo;
					var orderlines = order_line_for_this_combo;
					var sum_line_qty = 0;
					var combo_line_used = [];	
					for (var i=0;i<orderlines.length;i++){
						var product = orderlines[i].product;
						if(orderlines[i].waiting_combo_line_id){
							if(line.id == orderlines[i].waiting_combo_line_id){
								if(line.qty_combo <= orderlines[i].quantity){
									combo_line_used.push(orderlines[i].waiting_combo_line_id);
								}
								sum_line_qty = sum_line_qty + orderlines[i].quantity;
							}
						}else{
							if(line.product_list_ids.indexOf(product.id)>=0 && !combo_line_used.includes(line.id)){
								orderlines[i].waiting_combo_line_id = line.id;
								if(line.qty_combo <= orderlines[i].quantity){
									combo_line_used.push(line.id);
								}
								sum_line_qty = sum_line_qty + orderlines[i].quantity;
							}
						}
						if(sum_line_qty > line.qty_combo){
							var quantity_fix = orderlines[i].quantity - (sum_line_qty - line.qty_combo);
							orderlines[i].set_quantity(quantity_fix,true);
						}
						if(sum_line_qty >= line.qty_combo){
							combo_line_used.push(line.id)
						}
					}
                })
                // Lặp theo từng line trong Order
                var order_line_to_compute = [];
                var unfinished_qty_list_product = [];
                var unfinished_qty_cate_product = [];
//				var combo_line_used = [];		
                _.each(order_line_for_this_combo,function(line){
                    var product_id = line.product.id;
                    var qty = line.quantity;
                    // Lặp theo từng combo_line để kiểm tra số lượng
					var check_line = false;
					var combo_line_to_compute_limit = [];
					if(line.waiting_combo_line_id){
						var combo_checked = self.pos.db.combo_lines.filter(function(l){
							return l.id == line.waiting_combo_line_id;
						})
//						combo_line_used.push(line.waiting_combo_line_id)
						combo_line_to_compute_limit = combo_checked;
					}
//					else{
//						combo_line_to_compute_limit = combo_line_to_compute.filter(function(item){return !combo_line_used.includes(item.id)});
//					}
                    _.each(combo_line_to_compute_limit,function(combo_line){
                        if (!check_line){
                            if (combo_line.product_list_ids.indexOf(product_id)>=0){
								var combo_price = 0;
								var check_use_price_combo = false;
								if(combo_line.use_pricelist){
									combo_price = line.price;
								}else{
									var line_detail = self.pos.db.combo_lines_detail.filter(function(line){
										return line.sale_promo_combo_line_id[0] == combo_line.id && line.product_id[0] == product_id;
									})
									if(line_detail.length){
										combo_price = line_detail[0].unit_price_combo;
										check_use_price_combo = true;
									}
								}
                                if(combo_line.qty_combo == qty ){
                                    order_line_to_compute.push({
                                        line:line,
                                        price:combo_price,
                                        combo_line:combo_line,
										check_use_price_combo:check_use_price_combo
                                    });
                                } else if (combo_line.qty_combo > qty){
                                    unfinished_qty_list_product.push({
                                        line:line,
                                        price:combo_price,
                                        combo_line:combo_line,
										check_use_price_combo:check_use_price_combo
                                    });
                                } else if (combo_line.qty_combo < qty){
                                    line.set_quantity(combo_line.qty_combo,true);
                                    unfinished_qty_list_product.push({
                                        line:line,
                                        price:combo_price,
                                        combo_line:combo_line,
										check_use_price_combo:check_use_price_combo
                                    });
                                }
								check_line = true;
                                
                            }
                        }
                    })
                })
                var unfinished_orderlines_2_delete = []
                _.each(combo_line_to_compute,function(combo_line){
                    var total_qty = combo_line.qty_combo;
                    var unfinished_orderlines = []
                    var unfinished_orderlines_qty = 0;
                   	if(unfinished_qty_list_product.length>0){
                        unfinished_orderlines = unfinished_qty_list_product.filter(function(item){
                            return item.combo_line.id == combo_line.id
                        })
                    }
                    _.each(unfinished_orderlines, function(item){
                        unfinished_orderlines_qty += item.line.quantity;
                    })
                    if (unfinished_orderlines_qty >= total_qty){
                        _.each(unfinished_orderlines,function(i){
                            order_line_to_compute.push(i);
                        })
                    } else{
                        _.each(unfinished_orderlines,function(i){
                            unfinished_orderlines_2_delete.push(i);
                        })
                    }
                })
                var total_line_qty = 0;
                _.each(order_line_to_compute, function(item){
                    total_line_qty += item.line.quantity;
                })
                if(total_combo_qty <= total_line_qty){
                    _.each(unfinished_orderlines_2_delete, function(item){
                        self.remove_orderline(item.line);
                    })
                    _.each(order_line_to_compute, function(line){
                        var order_line = line.line;
						order_line.check_use_price_combo = line.check_use_price_combo;
                        order_line.set_price(line.price);
                        order_line.set_combo_qty(1);
                        order_line.set_is_done_combo(true);
                        order_line.set_combo_line(line.combo_line);
                        order_line.set_combo_seq(combo_seq);
                    })
                    combo_seq += 1;
                    return_true = false;
                }
            })
            return return_true
        },
        //Get coupon by combo
        get_coupon_by_code_w_combo: function(code,search_type){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines();
        	var gui_order = self.pos.chrome.gui;
        	var backend_id = self.pos.config.warehouse_id
        	if(order.coupon_code && code['code']==order.coupon_code){
        		return gui_order.show_popup('error',_t('Coupon đã được nhập !!'));
        	}
        	
        	var apply_coupon = true;
			rpc.query({
                model: 'crm.voucher.publish',
                method: 'check_coupon_apply_combo',
                args: [code,backend_id[0]],
            })
            .then(function (result_from_server) {
            	var result_from_server = result_from_server;
				var error = '';
				if (!result_from_server.length){
					return self.get_coupon_by_code(code,search_type);
				}
				if (result_from_server[0]=='employee'){
					error = 'Vui lòng dùng chức năng Coupon Nhân viên để sử dụng Coupon này';
					return gui_order.show_popup('error',_t(error));
				}
				if (result_from_server[0]=='product_coupon'){
					error = 'Coupon không áp dụng bằng phương thức này, vui lòng kiểm tra lại';
					return gui_order.show_popup('error',_t(error));
				}
				if (result_from_server[0]=='date'){
					error = 'Coupon đã hết hạn (' + result_from_server[1] + '), Vui lòng kiểm tra lại !!';
					return gui_order.show_popup('error',_t(error));
				}
				if (result_from_server[0]=='count'){
					error = 'Coupon đã hết xài hết số lần sử dụng cho phép !! (Đã sử dụng: ' +  result_from_server[1] + ' lần)';
					return gui_order.show_popup('error',_t(error));
				}
				if (result_from_server[0]=='combo'){
					var combo_id = result_from_server[4];
					var combo = self.pos.db.get_combo_by_id(combo_id);
					if(!combo){
						error = 'Combo áp dụng cho coupon không khả dụng';
						return gui_order.show_popup('error',_t(error));
					}
					var notify =  ['Thẻ hợp lệ, vui lòng xác nhận để sử dụng !',
						  'Ngày hết hạn: ' + result_from_server[1] || '',
						  'Số lần đã sử dụng: ' + result_from_server[2]]
					gui_order.show_popup('confirm',{
		                'title': _t('Coupon Combo'),
		                'body':  notify,
						'error': 'Số lần còn lại: ' + result_from_server[3],
		                'confirm': function(){
		                	order.set_coupon_code(code.code);
		                	order.use_coupon = true;
		                	var numpad = self.pos.chrome.screens.products.numpad;
		                	var product_categories_widget = self.pos.chrome.screens.products.product_categories_widget;
		                	order.set_combo_coupon(combo_id, code.code);
		                	numpad.show_combo_list(true, combo_id);
		                	product_categories_widget.set_combo(combo_id);
		                	product_categories_widget.renderElement(true,combo_id);
		                },
					    'cancel': function(){
					    	if(!order.coupon_code_array.length){
					    		order.unset_promotion_for_coupon();
						    	order.compute_promotion_after_reset_price();
					    	}
					    }
		            });
				}
            },function(error){
				error.event.preventDefault();
				gui_order.show_popup('error',{
	                'title': _t('Error: Could not Save Changes'),
	                'body': _t('Your Internet connection is probably down.'),
	            });
	        });
        },
		remove_combo_done: function(){
			var order = this;
			var line_in_combo = order.orderlines.models.filter(function(line){
                return line.is_done_combo == true && line.combo_id});
			if (line_in_combo.length > 0){
				_.each(line_in_combo, function(line){
					//remove combo header
					if(line.node){
						var header_node = line.node.previousElementSibling;
						if(header_node && !$(header_node).hasClass('orderline')){
							header_node.parentNode.removeChild(header_node);
						}
					}
                    order.remove_orderline(line);
                })
			}
		},
		
		get_new_price : function(product,qty,orderline=false){
			if(orderline && orderline.combo_id && orderline.is_done_combo){
				return;
			}
			var new_price = _super_order.get_new_price.apply(this,arguments);
			return new_price
		}
        
    });
});