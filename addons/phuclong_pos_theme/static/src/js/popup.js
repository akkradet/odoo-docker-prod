odoo.define('phuclong_pos_theme.popups', function (require) {
    "use strict";
    var PopupWidget = require('point_of_sale.popups');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    
	PopupWidget.include({
	    show: function(options){
	        options = options || {};
	        this._super(options);
			if(options && options.title == 'Ghi chú'){
				$('body').off('keypress', this.keyboard_handler);
	            window.document.body.removeEventListener('keypress',this.keyboard_handler);
	            $('body').off('keydown', this.keyboard_handler);
	            window.document.body.removeEventListener('keydown',this.keyboard_handler);
			}
	    },
	});

    var SaletypeSelectionPopupWidget = PopupWidget.extend({
        template: 'SaletypeSelectionPopupWidget',
        show: function(options){
            var self = this;
            options = options || {};
            this._super(options);
    
            this.list = options.list || [];
            this.is_selected = options.is_selected || function (item) { return false; };
            this.renderElement();
        },
        click_item : function(event) {
            this.gui.close_popup();
            if (this.options.confirm) {
                var item = this.list[parseInt($(event.currentTarget).data('item-index'))];
                item = item ? item.item : item;
                this.options.confirm.call(self,item);
            }
        }
    });
    gui.define_popup({ name:'saletype', widget: SaletypeSelectionPopupWidget});
    
    var ClientMethodPopupWidget = PopupWidget.extend({
        template: 'ClientMethodPopupWidget',
        show: function(options){
            options = options || {};
            var self = this;
            var order = this.pos.get_order();
            this._super(options);
//            this.renderElement();
            $('.item-method.card').click(function () {
            	order.set_check_scan_card_customer(true);
				self.gui.chrome.screens.clientlist.reload_partners();
            	self.gui.show_popup('cardscanner',{
        	    	title: 'Xin hãy quẹt thẻ khách hàng vào máy quét'
        	    });
            });
            $('.item-method.keyboard').click(function () {
            	order.set_check_keyboard_customer(true);
            	self.gui.show_popup('cardscanner',{
        	    	title: 'Xin hãy quẹt thẻ Quản lý cửa hàng vào máy quét'
        	    });
            })
            $('.btn-deny.cancel').click(function () {
            	self.click_confirm();
            })
        },
        click_confirm: function(){
        	var order = this.pos.get_order();
        	order.set_check_scan_card_customer(false);
        	order.set_check_scan_card_customer(false);
            this.gui.close_popup();
            if (this.options.cancel) {
                this.options.cancel.call(this);
            }
        },
    });
    gui.define_popup({ name:'clientmethod', widget: ClientMethodPopupWidget});
    
    var CouponMethodPopupWidget = PopupWidget.extend({
        template: 'CouponMethodPopupWidget',
        show: function(options){
            options = options || {};
            var self = this;
            var order = this.pos.get_order();
            var orderlines = order.orderlines;
            this._super(options);
            $('.item-method.coupon-edit').click(function () {
            	self.gui.show_popup('textinput',{
        	    	title: _t('Nhập mã Coupon'),
        	    	confirm: function(code) {
        	    		var coupon_code = ({code:code});
        	    		var search_type = 'coupon';
        	    		order.get_coupon_by_code_w_combo(coupon_code,search_type);
        	    	},
        	    	cancel: function() {
        	    		order.compute_promotion_after_reset_price();
        	    	},
        	    });
            });
            $('.item-method.coupon-cancel').click(function () {
            	var list = [];
                for (var i = 0; i < order.coupon_code_array.length; i++) {
                	var coupon_code = order.coupon_code_array[i];
                	var coupon_code_label = coupon_code
                	if(order.current_coupon_code && order.current_coupon_code == coupon_code){
                		coupon_code_label = 'Coupon Nhân viên';
                	}
                    list.push({
                        label: coupon_code_label,
                        item: coupon_code,
                    });
                }
                self.gui.show_popup('selection',{
                    'title': 'Vui lòng chọn Coupon cần hủy',
                    'list': list,
                    'confirm': function(coupon_code){
                    	var line_coupon_combo = orderlines.filter(function(line) 
        					{return line.is_done_combo == true && line.combo_id && line.combo_coupon_code == coupon_code}
        	    		);
                    	if(line_coupon_combo.length){
                    		_.each(line_coupon_combo, function(line){
                                order.remove_orderline(line);
                            })
                    	}else{
                    		if(order.coupon_promotion_array.length){
                        		var promotion_coupon = order.coupon_promotion_array.filter(function(line) 
                					{return line.code == coupon_code}
                	    		);
                        		if(promotion_coupon.length){
                        			var promotion_line_id = promotion_coupon[0].promotion_line;
                        			var promotion_existed = order.coupon_promotion_array.filter(function(line) 
                    					{return line.promotion_line == promotion_line_id && line.code != coupon_code}
                    	    		);
                        			if(!promotion_existed.length){
                        				order.reset_promotion_line(promotion_line_id);
                        			}
                        		}
                        	}
                    	}
                    	
                        order.unset_coupon_code(coupon_code);
                        order.compute_promotion();
                    },
                });
            })
            $('.btn-deny.cancel').click(function () {
            	self.click_confirm();
            })
        },
        click_confirm: function(){
            this.gui.close_popup();
            if (this.options.cancel) {
                this.options.cancel.call(this);
            }
        },
    });
    gui.define_popup({ name:'couponmethod', widget: CouponMethodPopupWidget});

    var CardScannerPopupWidget = PopupWidget.extend({
        template: 'CardScannerPopupWidget',
        show: function(options){
        	var self = this;
            options = options || {};
            this._super(options);
//            this.renderElement();
            $('.btn-deny.cancel').click(function () {
            	self.click_confirm();
            })
        },
        click_confirm: function(){
        	var order = this.pos.get_order();
        	order.unset_check_scan();
            this.gui.close_popup();
            if (this.options.cancel) {
                this.options.cancel.call(this);
            }
        },
    });
    gui.define_popup({ name:'cardscanner', widget: CardScannerPopupWidget});

    var selectPromotionPopupWidget = PopupWidget.extend({
        template: 'selectPromotionPopupWidget',
        show: function(options){
        	var self = this;
        	this.popup_select_promotion = true;
        	this.orderlines = options.orderlines || [];
            this.promotion_ids = options.promotion_ids || [];
			this.promotion_all_ids = options.promotion_all_ids || [];
            options = options || {};
            this._super(options);
            $('.btn-deny.cancel').click(function () {
            	self.click_cancel();
            })
            $('.btn-accept').click(function () {
            	self.click_confirm();
            })
            $('input:checkbox[name="promotion"]').change(function() {
                self.onchange_promotion_product(this);
            });
            $('select[name="promotion"]').change(function() {
                self.onchange_promotion_line(this);
            });
			self.update_checked_promotion();
//            this.renderElement();
        },
		uncheck_all: function(){
			var all_checkbox_node = $('input:checkbox[name="promotion"]');
			_.each(all_checkbox_node, function(node){
				if(node.checked){
					node.checked = false;
				}
			})
			var all_selection_node = $('select[name="promotion"]');
			_.each(all_selection_node, function(node){
				if(node.value != 0){
					$(node).val(0);
				}
			})
		},
		check_all: function(promotion_id){
			var all_checkbox_node = $('input:checkbox[name="promotion"]');
			_.each(all_checkbox_node, function(node){
				if(!node.checked){
					node.checked = true;
				}
			})
			var all_selection_node = $('select[name="promotion"]');
			_.each(all_selection_node, function(node){
				if(node.value != promotion_id){
					$(node).val(promotion_id);
				}
			})
		},
		update_checked_promotion: function(){
			var all_checkbox_node = $('input:checkbox[name="promotion"]');
			var has_promotion = false;
			_.each(all_checkbox_node, function(node){
				if(node.checked && node.value != 'promotion_all'){
					all_checkbox_node[0].checked = true;
					has_promotion = true;
					return;
				}
			})
			if(!has_promotion && all_checkbox_node[0].checked){
				all_checkbox_node[0].checked = false;
				var all_selection_node = $('select[name="promotion"]');
				if(all_selection_node[0].value!=0){
					$(all_selection_node[0]).val(0);
				}
			}
		},
        onchange_promotion_product: function(node){
        	var self = this;
        	var node_promotion = $('select[id=' + node.value + ']');
        	var promotion_selected = node_promotion.val();
        	if(promotion_selected!=0){
        		if(!node.checked){
        			node_promotion.val(0);
        		}
        	}else{
        		if(node.checked){
        			node.checked = false;
					return;
        		}
        	}
			if(node.value == 'promotion_all' && !node.checked){
				self.uncheck_all();
			}
			self.update_checked_promotion();
        },
        onchange_promotion_line: function(node){
        	var self = this;
        	var node_product = $('input:checkbox[value=' + node.id + ']')[0];
        	var promotion_selected = node.value;
        	var node_promotion = $('select[id=' + node.id + ']');
        	node_promotion.removeClass('promotion-fault');
        	if(promotion_selected!=0){
        		if(!node_product.checked){
        			node_product.checked = true;
        		}
				if(node.id == 'promotion_all'){
					self.check_all(node.value);
				}
        	}else{
        		if(node_product.checked){
        			node_product.checked = false;
        		}
				if(node.id == 'promotion_all'){
					self.uncheck_all();
				}
        	}
			self.update_checked_promotion();
        },
        click_confirm: function(){
        	var self = this;
//        	this.gui.close_popup();
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines()
        	var promotion_to_update = [];
        	var loyalty_to_update = [];
        	var loyalty_to_remove = [];
            var promotion_line_list = $('select[name="promotion"]');
            var check_promotion_fault = false;
            var create_log_line = [];
            if(promotion_line_list){
            	for(var i=0; i < promotion_line_list.length; i++){
            		var line_id = promotion_line_list[i].id;
            		var line_selected = orderlines.filter(function(line) 
    					{return line.id == line_id}
    	    		);
            		if(!line_selected.length){
            			continue;
            		}
            		line_selected = line_selected[0];
            		var line_promotion_id = promotion_line_list[i].value;
            		if(line_promotion_id == 'loyalty'){
            			if(!line_selected.loyalty_discount_percent){
            				loyalty_to_update.push(line_selected);
            			}
            		}else{
            			if(line_promotion_id == 0 && line_selected.loyalty_discount_percent){
            				loyalty_to_remove.push(line_selected);
            			}else{
            				if(line_selected.loyalty_discount_percent){
            					loyalty_to_remove.push(line_selected);
            				}
            				var existed_promotion = promotion_to_update.filter(function(line) 
            					{return line[0] == line_promotion_id}
            	    		);
                    		if(!existed_promotion.length){
                    			promotion_to_update.push([line_promotion_id, [line_id]]);
                    		}else{
                    			existed_promotion[0][1].push(line_id);
                    		}
            			}
            		}
            	}
				//Remove Loyalty
            	if(loyalty_to_remove.length){
            		for(var i in loyalty_to_remove){
            			order.remove_loyalty_discount(loyalty_to_remove[i]);
            			loyalty_to_remove[i].set_disable_loyalty(true);
            			create_log_line.push(loyalty_to_remove[i]);
            		}
				}
            	//Update promotion
            	if(promotion_to_update.length){
            		//1: Check all promotion on new select are available
            		for(var i in promotion_to_update){
            			var promotion_line_id = promotion_to_update[i][0];
            			var lines = promotion_to_update[i][1];
            			var orderline_to_update = [];
            			for(var order_line_id in lines){
            				var line_id = lines[order_line_id];
            				for(var line in orderlines){
                    			if(orderlines[line].id == line_id && orderlines[line].promotion_line_id != promotion_line_id && promotion_line_id!=0){
                					orderline_to_update.push(orderlines[line]);
                    				break;
                    			}
                    		}
            			}
            			//check promotion per promoline
            			var promo_line_id = self.pos.promotion_lines[promotion_line_id];
						if(promo_line_id!=undefined && promo_line_id.length && orderline_to_update.length){
			    			for(var i in orderline_to_update){
			    				if(orderline_to_update[i].promotion_available){
			    					orderline_to_update[i].set_promotion_available(false);
			    				}
			    			}
							var line = order.check_promotion_no_condition([promo_line_id[0]], false, orderline_to_update);
							var check_promotion_success = true;
							if(line){
								var check_condition_lines = orderline_to_update.filter(function(l) 
			        				{return !l.promotion_available;}
		        	    		);
								if(check_condition_lines.length){
									check_promotion_success = false;
								}
		    				}else{
		    					check_promotion_success = false;
		    				}
							
							if(!check_promotion_success){
								for(var l in orderline_to_update){
									if(!orderline_to_update[l].promotion_available){
										var promotion_fault = $('select[id=' + orderline_to_update[l].id+ ']');
										if(promotion_fault.length){
											promotion_fault.addClass('promotion-fault');
										}
									}
	        					}
		    					check_promotion_fault = true;
							}
						}
            		}
            		//Return if any check fault
            		if(check_promotion_fault){
            			return;
            		}else{
            			this.gui.close_popup();
            		}
            		
            		//2: Set promotion by user selection
            		var geted_promotions = [];
            		var promoline_to_reset = [];
					var single_line_to_reset = [];
            		var orderline_disable_promotion = []
            		for(var i in promotion_to_update){
            			var promotion_line_id = promotion_to_update[i][0];
						var promo_line_obj = false;
            			var lines = promotion_to_update[i][1];
            			var orderline_to_update = [];
            			for(var order_line_id in lines){
            				var line_id = lines[order_line_id];
            				for(var line in orderlines){
                    			if(orderlines[line].id == line_id && orderlines[line].promotion_line_id != promotion_line_id){
                    				create_log_line.push(orderlines[line]);
                    				var check_reset = false;
                    				if(orderlines[line].promotion_line_id && !promoline_to_reset.includes(orderlines[line].promotion_line_id)){
                    					check_reset = true;
                					}
                    				if(orderlines[line].promotion_line_id && promotion_line_id==0){
                    					orderline_disable_promotion.push(orderlines[line]);
                    					if(check_reset){
											promo_line_obj = self.pos.promotion_lines[orderlines[line].promotion_line_id][0];
											if(promo_line_obj.is_product_coupon_promotion){
												single_line_to_reset.push(orderlines[line]);
											}else{
												promoline_to_reset.push(orderlines[line].promotion_line_id)
											}
                    					}
                    				}else{
                    					if(check_reset){
											promo_line_obj = self.pos.promotion_lines[orderlines[line].promotion_line_id][0];
											if(promo_line_obj.is_product_coupon_promotion){
												orderlines[line].remove_discount_line(true);
												order.get_new_price(orderlines[line].product, orderlines[line].quantity, orderlines[line].orderline);
											}else{
												order.reset_promotion_line(orderlines[line].promotion_line_id);
											}
                    					}
                    					var line_after_reset = orderlines.filter(function(l) 
                        					{return l.id == line_id;}
                        	    		);
                    					if(line_after_reset.length){
                    						orderline_to_update.push(line_after_reset[0]);
                    					}
                    				}
                    				break;
                    			}
                    		}
            			}
            			
            			//set promotion per promoline
            			var promo_line_id = self.pos.promotion_lines[promotion_line_id];
						if(promo_line_id!=undefined && promo_line_id.length && orderline_to_update.length){
							var line = order.check_promotion_no_condition([promo_line_id[0]], true, orderline_to_update);
							if(line){
								for(var l in orderline_to_update){
									orderline_to_update[l].set_disable_promotion(false);
	        					}
		    					geted_promotions.push(line);
		    				}
						}
            		}
            		//reset promoline
        			if(promoline_to_reset.length){
        				for(var i in promoline_to_reset){
        					order.reset_promotion_line(promoline_to_reset[i]);
        				}
        			}
					//reset single line
					if(single_line_to_reset.length){
        				for(var i in single_line_to_reset){
							single_line_to_reset[i].remove_discount_line(true);
							order.get_new_price(single_line_to_reset[i].product, single_line_to_reset[i].quantity, single_line_to_reset[i].orderline);
        				}
        			}
					
            		//disable update promotion for these line
        			if(orderline_disable_promotion.length){
        				for(var i in orderline_disable_promotion){
        					orderline_disable_promotion[i].set_disable_promotion(true);
        				}
        			}
        			var promo_ids = [];
					//dont compute promotion if have discount all order on select
					var check_compute_promotion = true;
            		if (geted_promotions.length){
            			var promotion_lines = geted_promotions;
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
								if(promotion_lines[i].product_attribute == 'order'){
									check_compute_promotion = false;
								}
            					order.get_promotion_by_line(promo_ids,promotion_lines[i],0);
            				}
            			}
            	    	//Promotion gift
                		if(promo_ids.length){
        	    			promo_ids = _.sortBy(promo_ids,function(line){return line.benefit_type;});
            	    		order.get_promotion_by_line(promo_ids,promo_ids[0],0);
            	    	}
            		}

					//Compute promotion after all
					if(promotion_to_update.length && check_compute_promotion){
	        			order.compute_promotion();
					}
            	}
            	//Update Loyalty
            	if(loyalty_to_update.length || loyalty_to_remove.length){
            		for(var i in loyalty_to_update){
            			loyalty_to_update[i].set_disable_loyalty(false);
            			create_log_line.push(loyalty_to_update[i]);
            		}
//            		for(var i in loyalty_to_remove){
//            			order.remove_loyalty_discount(loyalty_to_remove[i]);
//            			loyalty_to_remove[i].set_disable_loyalty(true);
//            			create_log_line.push(loyalty_to_remove[i]);
//            		}
            		order.checked_loyalty_level = false;
                	order.set_unchecked_disc_loyalty();
                	order.set_unchecked_disc_birthdate();
                	self.chrome.screens.payment.get_loyalty();
            	}
				
            	//Create Log
            	if(create_log_line.length){
            		for(var i in create_log_line){
            			order.log_history_permisson('change_promotion', false, false, create_log_line[i].product.id);
            		}
            	}

				//Remove Loyalty close popup no promotion
            	if(loyalty_to_remove.length && !promotion_to_update.length){
            		this.gui.close_popup();
				}
				
				//Remove loyalty if exist promotion_all_order
				if(!order.check_condition_loyalty_order()){
					order.remove_loyalty_discount();
				}

				this.pos.chrome.screens.products.order_widget.renderElement();
            }
        }
    });
    gui.define_popup({ name:'select_promotion_widget', widget: selectPromotionPopupWidget});
 

    var ToppingPopupWidget = PopupWidget.extend({
        template: 'ToppingPopupWidget',
        show: function(options){
            options = options || {};
			var order = this.pos.get_order();
            this._super(options);
            this.product = options.product || [];
			if(this.product){
				if(order.locked_products.indexOf(this.product.product_tmpl_id) >= 0){
					return this.pos.chrome.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Sản phẩm này đang nằm trong danh sách khóa món của cửa hàng',
			        });
				}
			}
            this.orderline = options.orderline || false;
            this.product_price = 0;
            this.default_qty = options.default_qty || 1;
            this.default_topping_list = options.default_topping_list || [];
            this.cup_type_default = options.cup_type_default || false;
            //Promotion info
            this.is_promotion_product = options.is_promotion_product || false;
            this.lists_template_promo = options.lists_template_promo || [];
            this.promotion_loop_type = options.promotion_loop_type || '';
            this.promotion_ids = options.promotion_ids || [];
            this.promo_line = options.promo_line || false;
            this.qty_rewared = options.qty_rewared || 0;
            this.benefit_qty_total = options.benefit_qty_total || 0;
            this.promotion_name = '';
			this.benefit_lines = options.benefit_lines || [];
			this.promotion_price = options.promotion_price || 0;
            //loyalty info
            this.is_loyalty_line = options.is_loyalty_line || false;
            this.new_price = options.new_price || 0;
            this.reward = options.reward || false;
            this.is_birthday_promotion = options.is_birthday_promotion || false;
            this.loyalty_point_cost = options.loyalty_point_cost || 0;
			//combo
			this.is_done_combo = options.is_done_combo || false;
			var combo = this.pos.chrome.screens.products.product_categories_widget.combo;
            this.combo_id = combo ? combo : false;
			if((this.promotion_loop_type == 'none' || (this.promotion_loop_type == 'multi_benefit_lines' && this.lists_template_promo.length == 1))
				&& this.benefit_qty_total>1){
        		this.default_qty = this.benefit_qty_total;
        	}
			this.cashless_code = options.orderline ? options.orderline.cashless_code : false;
			this.product_coupon_code = options.orderline ? options.orderline.product_coupon_code : '';
            this.renderElement();
			if(this.cup_type_default == 'themos' && this.product_coupon_code){
				var product_coupon_apply = $('.product_coupon_apply');
				product_coupon_apply.removeClass('oe_hidden');
			}
        },
        renderElement: function(material_list, topping_list_checked) {
        	var self = this;
            var order = this.pos.get_order();
        	if(this.product && !this.is_promotion_product){
            	this.product_price = order.get_new_price(this.product,1);
            }
        	if(this.is_loyalty_line){
            	this.product_price = order.get_new_price(this.product,1) - this.new_price;
            }
			if(this.product && this.is_promotion_product && this.promotion_price){
            	this.product_price = this.promotion_price;
            }
        	if(this.is_promotion_product && this.promo_line && this.promo_line.promotion_id){
        		var promotion_id = order.get_promo_header_by_id(this.promo_line.promotion_id[0]);
        		this.promotion_name = promotion_id.name;
        	}

			this.material_list_default = [];
			if(material_list){
				this.material_list_default = material_list;
			}
			
			if(topping_list_checked && !this.orderline){
				this.default_topping_list = topping_list_checked;
			}

            this._super();
			//reset topping default
			if(!this.orderline){
				this.default_topping_list = [];
			}
            $('.btn-minus').click(function () {
                const _self = $(this);
                let valAmount = _self.parent().find('.amount-number');
                if(valAmount.val() <= 1) {
                    return valAmount.val(1);
                }
                valAmount.val(parseInt(valAmount.val()) - 1);
                self.update_popup_summary();
            })
            $('.btn-plus').click(function () {
                const _self = $(this);
                let valAmount = _self.parent().find('.amount-number');
        
                valAmount.val(parseInt(valAmount.val()) + 1);
                self.update_popup_summary();
            })
			$('.close-topping').click(function () {
                self.click_cancel();
            })
            //Onchange size
            $('input:radio[name="size"]').change(function() {
                self.onchange_size(this.value);
            });
            //Onchange topping
            $('input:checkbox[name="topping"]').change(function() {
                self.onchange_topping();
            });
			$('input:radio[name="cup"]').change(function() {
                self.onchange_cup();
            });
            this.update_popup_summary();
            
        },
		onchange_cup: function(){
			var cup_list = $('input:radio[name="cup"]');
            if(cup_list){
            	for(var c in cup_list){
					if(cup_list[c].value == 'cup_themos'){
						var product_coupon_apply = $('.product_coupon_apply');
						if(cup_list[c].checked){
							product_coupon_apply.removeClass('oe_hidden');
							var scrollingElement = $('.wrap-list-option');
							scrollingElement[0].scrollTop = scrollingElement[0].scrollHeight;
						}else{
							product_coupon_apply.addClass('oe_hidden');
							$('.product-coupon-apply').val('');
						}
					}
            	}
            }
		},
        onchange_size : function(product_id) {
			var self = this;
			this.cup_type_default = false;
        	var product = this.pos.db.get_product_by_id(product_id);
        	this.product = product;
			//keep material
			var material = $('input:radio[class="radio-input material"]');
            var material_list = [];
            
            if(material){
            	for(var ml in material){
            		if(material[ml].checked){
						var material_product = self.pos.db.material_ids[material[ml].name];
            			var material_name = material_product.name;
            			var material_value = {
            				'option_name':material_name,
            				'option_type': material[ml].value
            			}
            			material_list.push(material_value);
            		}
            	}
            }

			var topping_list_checked = [];
			//keep topping
			var topping_list = $('input:checkbox[name="topping"]');
            if(topping_list){
            	for(var tp in topping_list){
            		if(topping_list[tp].checked){
						var topping_product = self.pos.db.get_product_by_id(topping_list[tp].value);
            			topping_list_checked.push(topping_product.id);
            		}
            	}
            }
			//remove coupon
			$('.product-coupon-apply').val('');
			if(this.product_coupon_apply){
				this.product_coupon_apply = '';
			}
			
        	this.renderElement(material_list, topping_list_checked);
        },
        onchange_topping : function() {
        	var self = this;
        	self.update_popup_summary();
        },
        update_popup_summary: function(){
        	var self = this;
        	var order = this.pos.get_order();
            var product = this.product;
            var product_price = this.product_price;
            var topping_list = $('input:checkbox[name="topping"]');
            if(topping_list){
            	for(var tp in topping_list){
            		if(topping_list[tp].checked){
            			var topping_product = self.pos.db.get_product_by_id(topping_list[tp].value);
            			if(topping_product){
            				var topping_price = order.get_new_price(topping_product,1) || 0;
            				product_price += topping_price;
            			}
            		}
            	}
            }
            var quantity = this.$el.find('.amount-number').val() || 0;
            product_price = product_price*quantity;
            	
            var $total = this.el.querySelector('.wrap-total > .cash');
            if($total){
            	$total.textContent = this.format_currency(product_price);
            }
        },

		get_coupon_by_code_selected_product: function(code, product, qty){
            var self = this;
            var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
            var gui_order = self.pos.chrome.gui;
            var backend_id = self.pos.config.warehouse_id
            var error_mess = this.$el.find('.product-coupon-apply-error-mess')[0];
            rpc.query({
                model: 'sale.promo.header',
                method: 'check_coupon_apply_product',
                args: [code,backend_id[0]],
            })
            .then(function (result_from_server) {
                var result_from_server = result_from_server;
                var error = '';
                if (!result_from_server.length){
					error_mess.textContent  = "Vui lòng kiểm tra lại Coupon";
					return;
                }
                if (result_from_server[0]=='date'){
                    error = 'Coupon đã hết hạn (' + result_from_server[1] + '), Vui lòng kiểm tra lại !!';
					error_mess.textContent = error;
                    return;
                }
                if (result_from_server[0]=='count'){
                    error = 'Mã Coupon đã sử dụng hết số lần cho phép: ' + result_from_server[1] + ' lần)';
                    error_mess.textContent = error;
                    return;
                }
				var all_promotion_lines = [];
                var promo_header = order.get_promo_header_by_id(result_from_server[4]);
				if(promo_header && promo_header.use_for_coupon && order.check_promo_header(promo_header)){
					var now = new Date();
					now.format("yy/M/dd");
					var hours = now.getHours();
					var minute = now.getMinutes();
					var float_now = hours + minute/60;
					var apply_any_time = false;
					if ((promo_header.start_hour == promo_header.end_hour) && promo_header.start_hour == 0){
						apply_any_time = true;
					}
					if ((promo_header.start_hour <= float_now && promo_header.end_hour >= float_now) || apply_any_time == true){
						var promotion_lines = [];
						if (promo_header.list_type == 'DIS'){
							promotion_lines = promo_header.discount_line;
						}else{
							promotion_lines = promo_header.promo_line;
						}
						_.each(promotion_lines,function(item){
							if (item){
								var promo_line_id = self.pos.promotion_lines[item];
								if(promo_line_id!=undefined && promo_line_id.length){
									if(promo_line_id[0].product_attribute!='order'){
										//check promoline
										if(order.check_promotion_line_with_product(promo_line_id[0], product, qty)){
											all_promotion_lines.push(promo_line_id[0]);
										}
									}
								}
							}
						});
					}
				}
                if (!all_promotion_lines.length){
					error_mess.textContent  = "Chương trình khuyến mãi của Coupon không khả dụng.";
                    return;
                }else{
					all_promotion_lines = _.sortBy(all_promotion_lines,function(line){
						return [(10000000000 + line.value_from), eval(line.discount_id != false).toString(), line.product_attribute, line.start_date_active, (10000000000 + line.discount_value)]
					}).reverse();
                    if(result_from_server[1] === false){
                        var notify =  [
                            'Thẻ hợp lệ, vui lòng xác nhận để sử dụng !',
                            'Số lần đã sử dụng: ' + result_from_server[2],
                        ]
                    } else{
                        var notify =  [
                            'Thẻ hợp lệ, vui lòng xác nhận để sử dụng !',
                            'Ngày hết hạn: ' + result_from_server[1],
                            'Số lần đã sử dụng: ' + result_from_server[2],
                        ]
                    }
					var promotion_limit = result_from_server[3];
                    gui_order.show_popup('confirm',{
                        'title': _t('Coupon '),
                        'body':  notify,
						'disable_cancel': true,
						'error': 'Số lần còn lại: ' + promotion_limit,
                        'confirm': function(){
							self.product_coupon_code = code;
							if(self.orderline){
								self.orderline.remove_discount_line(true);
//								var topping_line = orderlines.filter(function(tp_line) 
//									{return tp_line.is_topping_line && tp_line.related_line_id == self.orderline.id;}
//					    		);
//					    		if(topping_line.length){
//					    			for(var i in topping_line){
//					    				topping_line[i].remove_discount_line(true);
//					    			}
//					    		}
								order.remove_loyalty_discount(self.orderline);
								order.get_new_price(self.orderline.product, self.orderline.quantity, self.orderline);
							}
                            var line_id = self.click_confirm();
							line_id.set_disable_promotion(false);
							order.get_promotion_with_product_coupon(line_id, all_promotion_lines[0], promotion_limit);
                        },
                        'cancel': function(){
                            return;
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
        click_confirm: function(){
            // Thái: ràng buộc không đóng ca bán hàng của ngày hôm trước trước khi tạo đơn hàng mới
            var start_year = this.pos.pos_session.start_at.split(' ')[0].split('-')[0];
            var start_month = this.pos.pos_session.start_at.split(' ')[0].split('-')[1];
            var start_day = this.pos.pos_session.start_at.split(' ')[0].split('-')[2];
            var start_hour = this.pos.pos_session.start_at.split(' ')[1].split(':')[0];
            var start_minute = this.pos.pos_session.start_at.split(' ')[1].split(':')[1];
            var start_second = this.pos.pos_session.start_at.split(' ')[1].split(':')[2];
            var session_start_date_obj = new Date(parseInt(start_year),parseInt(start_month)-1,parseInt(start_day),parseInt(start_hour),parseInt(start_minute),parseInt(start_second));
            session_start_date_obj.setHours(session_start_date_obj.getHours() + 7);
            var session_start_date = session_start_date_obj.format('Y-m-d');
            var now_date = (new Date).format('Y-m-d');
            if (session_start_date != now_date){
                return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Bạn cần phải đóng ca bán hàng ngày cũ để mở ca ngày mới !!!',
                });
            }
        	var self = this;
        	var order = this.pos.get_order();
            var qty = this.$el.find('.amount-number').val();
            var selected_product = this.product;
			if (selected_product){
				//cashless loyalty
				if(selected_product.is_cashless){
					var cashless_code = this.$el.find('.cashless-code').val() || '';
					if(!this.cashless_code || this.cashless_code != cashless_code){
						var error_mess = this.$el.find('.cashless-error-mess')[0];
		                if(!cashless_code){
		                	error_mess.textContent  = "Vui lòng nhập mã thẻ nổi";
							return;
		                }
						return rpc.query({
			                model: 'pos.order',
			                method: 'check_cashless_code',
			                args: [cashless_code],
			            }).then(function(result_from_server){
							if (!result_from_server){
								error_mess.textContent  = "Mã thẻ không hợp lệ";
								return;
							}
							self.cashless_code = cashless_code;
							self.click_confirm();
				        },function(error){
							error.event.preventDefault();
							self.gui.show_popup('error',{
				                'title': _t('Error: Could not Save Changes'),
				                'body': _t('Your Internet connection is probably down.'),
				            });
				        });
					}
				}
				
				//product with coupon code
				if(selected_product.update_coupon_expiration){
					var backend_id = self.pos.config.warehouse_id;
					var product_coupon_code = this.$el.find('.product-coupon-code').val() || '';
					if(!this.product_coupon_code || this.product_coupon_code != product_coupon_code){
						var error_mess = this.$el.find('.cashless-error-mess')[0];
		                if(!product_coupon_code){
		                	error_mess.textContent  = "Vui lòng nhập mã Coupon";
							return;
		                }
						return rpc.query({
			                model: 'crm.voucher.publish',
			                method: 'check_coupon_product',
			                args: [product_coupon_code, backend_id],
			            }).then(function(result_from_server){
							if (!result_from_server){
								error_mess.textContent  = "Mã thẻ không hợp lệ";
								return;
							}
							self.product_coupon_code = product_coupon_code;
							self.click_confirm();
				        },function(error){
							error.event.preventDefault();
							self.gui.show_popup('error',{
				                'title': _t('Error: Could not Save Changes'),
				                'body': _t('Your Internet connection is probably down.'),
				            });
				        });
					}
				}
				
				//product apply coupon code
				var cup_list = $('input:radio[name="cup"]');
				var check_apply_coupon_product = false;
				var product_coupon_code = false;
	            if(cup_list){
	            	for(var c in cup_list){
						if(cup_list[c].value == 'cup_themos'){
							var product_coupon_code = $('.product_coupon_apply');
							if(cup_list[c].checked){
								check_apply_coupon_product = true;
								product_coupon_code = $('.product-coupon-apply').val();
								break;
							}
						}
	            	}
	            }
				if(check_apply_coupon_product){
					var backend_id = self.pos.config.warehouse_id;
					if(!this.product_coupon_code || this.product_coupon_code != product_coupon_code){
						var error_mess = this.$el.find('.product-coupon-apply-error-mess')[0];
		                if(!product_coupon_code){
		                	error_mess.textContent  = "Vui lòng nhập mã Coupon";
							return;
		                }
						//pricelist by cardcode
						var partner = order.get_client();
						if(partner && (partner.card_code_pricelist_id || partner.use_for_on_account)){
							error_mess.textContent  = "Coupon không áp dụng chung với thẻ khách hàng không tích điểm";
							return;
						}
						return self.get_coupon_by_code_selected_product(product_coupon_code, selected_product, qty);
					}
				}
				
				this.gui.close_popup();
                var combo = this.pos.chrome.screens.products.product_categories_widget.combo;
                var combo_id = combo ? combo : false;
                var combo_coupon_code = (order.combo_coupon_id && order.combo_coupon_code) ? order.combo_coupon_code : false;

                if(!this.is_promotion_product){
                	if(!this.is_loyalty_line){
                		var line_id = false;
                		if(!this.orderline){
                			line_id = order.add_product(selected_product,{
                                quantity:qty,
                                merge:false,
                                combo_id:combo_id,
                                disable_compute_promotion: true,
                            });
                		}else{
                			line_id = this.orderline;
                			//update orderline
                			
                			//#1: Quantity
                			if(qty != line_id.get_quantity()){
								if(line_id.is_promotion_line || line_id.is_birthday_promotion || line_id.get_reward()){
						    		return this.pos.chrome.gui.show_popup('alert',{
							              'title': 'ERROR',
							              'body':  'Bạn không có quyền điều chỉnh hàng khuyến mãi !',
							        });
						    	}
								if(line_id.promotion_line_id && line_id.check_reset_price_update_qty()){
					    			order.reset_promotion_line(line_id.promotion_line_id);
					    		}
                				line_id.set_quantity_no_compute(qty);
                			}
                			//#2: Size
                			if(this.product != this.orderline.product){
                				if(this.orderline.is_promotion_line || this.orderline.is_birthday_promotion || this.orderline.get_reward()){
                		    		return this.pos.chrome.gui.show_popup('alert',{
                			              'title': 'ERROR',
                			              'body':  'Bạn không có quyền điều chỉnh size hàng khuyến mãi !',
                			        });
                		    	}
								var topping_line_old =  this.orderline.get_topping_list(true);
//                				order.remove_orderline(this.orderline);
								order.orderlines.remove(this.orderline);
                                if(this.orderline.promotion_line_id){
                                    order.reset_promotion_line(this.orderline.promotion_line_id);
                                }
                                line_id = order.add_product(selected_product,{
                                    quantity:qty,
                                    merge:false,
                                    combo_id:combo_id,
                                    disable_compute_promotion: true,
                                });
								if(topping_line_old.length){
				    				for(var i in topping_line_old){
				    					topping_line_old[i].related_line_id = line_id.id;
				    				}
				    			}
                			}
                		}
                		if(combo_coupon_code){
                			line_id.set_combo_coupon_code(combo_coupon_code);
                		}
                	}else{
                		var line_id = new models.Orderline({}, {pos: self.pos, order: order, product: selected_product});
                		line_id.set_uom(selected_product.uom_id);
                		line_id.set_quantity_no_compute(1);
						order.get_new_price(selected_product,1,line_id);
                		if(this.new_price!=0){
                			line_id.set_discount_amount_line(this.new_price);
                		}else{
                			line_id.set_unit_price(this.new_price);
                		}
                		line_id.set_barcode_uom_relation(selected_product.barcode);
                		line_id.set_loyalty_line();
                		line_id.is_birthday_promotion = this.is_birthday_promotion;
                		line_id.loyalty_point_cost = this.loyalty_point_cost;
                		line_id.set_reward(this.reward);
            			order.orderlines.add(line_id);
                	}
                }else{
                	if((this.promotion_loop_type == 'none' || (this.promotion_loop_type == 'multi_benefit_lines' && this.lists_template_promo.length == 1))
						&& this.benefit_qty_total>1){
                		qty = this.benefit_qty_total;
                	}
                	var line_id = new models.Orderline({}, {pos: this.pos, order: order, product: selected_product});
                	line_id.set_uom(selected_product.uom_id);
                	line_id.set_quantity_no_compute(qty);
					order.get_new_price(selected_product,qty,line_id);
                	line_id.set_unit_price(this.promotion_price);
                	line_id.set_is_promotion_line();
                	line_id.set_promotion(this.promo_line.promotion_id, this.promo_line.id);
                	line_id.set_barcode_uom_relation(selected_product.barcode);
        			order.orderlines.add(line_id);
                }
                //Thai: check if combo selected
                var res = order.compute_combo();
//                this.pos.chrome.screens.products.order_widget.renderElement();
                if (res){
                    if(combo.id == order.combo_coupon_id){
                        this.pos.chrome.screens.products.product_categories_widget.renderElement(combo ? true:false, order.combo_coupon_id);
                    } else{
                        this.pos.chrome.screens.products.product_categories_widget.renderElement(combo ? true:false);
					}
					if(combo){
						this.pos.chrome.screens.products.product_categories_widget.set_combo(combo.id);
					}
                    
                } else{
                    var button_combo = $('.choose-combo');
                	var numpad = self.pos.chrome.screens.products.numpad;
                	if (button_combo.hasClass('open')){
                        var default_combo = self.pos.db.list_combo ? self.pos.db.list_combo[0] : false;
                        if (default_combo){
                            self.pos.chrome.screens.products.product_categories_widget.set_combo(default_combo.id);
                        }
                        numpad.show_combo_list(true);
                        button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                    } else if (button_combo.hasClass('closed')){
                    	numpad.show_combo_list(false, false, true);
                    }
                	if(order.combo_coupon_id){
                		order.set_combo_coupon(false);
                	}
                }
                
                var material_list_name = [];
                //Set cup_type orderline
                var cup_list = $('input:radio[name="cup"]');
                if(cup_list){
                	for(var c in cup_list){
                		if(cup_list[c].checked){
                			var cup_name = '';
                			if(cup_list[c].value != 0){
                				var cup_type = 'plastic';
                				if(cup_list[c].value == 'cup_paper_default' || cup_list[c].value == 'cup_paper'){
                					cup_type = 'paper';
                				}else if(cup_list[c].value == 'cup_themos'){
									cup_type = 'themos';
								}
                				line_id.set_cup_type(cup_type);
                				line_id.set_cup_type_default(cup_type);
                				
                				if(cup_list[c].value == 'cup_plastic'){
                					cup_name = 'Ly nhựa';
                				}
                				if(cup_list[c].value == 'cup_paper'){
                					cup_name = 'Ly giấy';
                				}
								if(cup_list[c].value == 'cup_themos'){
                					cup_name = 'Ly giữ nhiệt';
                				}
//                				cup_name = cup_product.display_name;
                			}else{
                				cup_name = 'Không lấy Ly';
                				line_id.set_cup_type_default('none');
								line_id.set_cup_type('none');
                			}
                			if(cup_name != ''){
                				material_list_name.push(cup_name);
                			}
                			break;
                		}
                	}
                }
                
                //Add custom material to orderline
                var material = $('input:radio[class="radio-input material"]');
                var material_list = [];
                
                if(material){
                	for(var ml in material){
                		if(material[ml].checked){
                			var material_value = {
                				'option_id':material[ml].name,
                				'option_type': material[ml].value
                			}
                			material_list.push(material_value);
                			var material_product = self.pos.db.material_ids[material[ml].name];
                			var material_name = material_product.name;
                			if(material[ml].value == 'none'){
                				material_list_name.push('Không ' + material_name);
                			}else if(material[ml].value == 'below'){
                				material_list_name.push('Ít ' + material_name);
                			}else if(material[ml].value == 'over'){
                				material_list_name.push('Nhiều ' + material_name);
                			}
                		}
                	}
                	line_id.set_custom_material_list(material_list);
                }
                
                if(material_list_name.length){
            		var material_name_display = material_list_name.join(', ');
            		line_id.set_material_name(material_list_name);
            	}else{
            		line_id.set_material_name([]);
            	}
                
                //Set note orderline
                var note = this.$el.find('.set-note-line').val() || '';
                if(note != line_id.note){
                	line_id.set_note(note);
                }

				if(this.cashless_code && line_id.cashless_code != this.cashless_code){
					line_id.cashless_code = this.cashless_code;
				}
				if(!check_apply_coupon_product && !selected_product.update_coupon_expiration){
					if(line_id.promotion_line_id && line_id.product_coupon_code){
						line_id.remove_discount_line(true);
						order.get_new_price(line_id.product, line_id.quantity, line_id);
					}
					this.product_coupon_code = '';
					line_id.product_coupon_code = '';
				}
				if(this.product_coupon_code && line_id.product_coupon_code != this.product_coupon_code){
					line_id.product_coupon_code = this.product_coupon_code;
				}
                
				//Add Topping to order
                var topping_list = $('input:checkbox[name="topping"]')
                var topping_list_name = [];
                var default_topping_list = this.default_topping_list || [];
                var topping_list_chosen = [];
                var topping_list_added = [];
				var topping_list_not_choose = [];
                var topping_list_remove = [];
                if(topping_list){
                	for(var tp in topping_list){
						var topping_product = self.pos.db.get_product_by_id(topping_list[tp].value);
                		if(topping_list[tp].checked){
                			topping_list_chosen.push(topping_product);
                		}else{
							topping_list_not_choose.push(topping_product);
						}
                	}
                }
                //#1 remove topping line
                topping_list_remove = default_topping_list.filter(function(tp){
					var product = self.pos.db.get_product_by_id(tp);
					return topping_list_not_choose.includes(product);
				});
                if(topping_list_remove.length){
                	var topping_orderlines = line_id.get_topping_list(true);
                	if(topping_orderlines.length){
            			for (var i=0; i < topping_orderlines.length; i++){
							if(topping_list_remove.includes(topping_orderlines[i].product.id)){
								order.orderlines.remove(topping_orderlines[i]);
							}
            			}
            		}
                }
                //#2 add topping line
                topping_list_added = topping_list_chosen.filter(function(tp){
					return !default_topping_list.includes(tp.id);
				});
	
//				var check_compute_promotion = false;
                if(topping_list_added.length){
                	for(var tp in topping_list_added){
            			var topping_product = topping_list_added[tp];
        				order.add_product(topping_product,{
                            quantity:qty,
                            merge:false,
							disable_compute_promotion: true,
							disable_selected:true,
                            extras: {related_line_id:line_id.id,
	                    		 	 is_topping_line:true}
                        });
//						check_compute_promotion = true;
//            			var topping_price_fm = self.format_currency_no_symbol(order.get_new_price(topping_product, 1));
//            			var topping_price_str = topping_price_fm.toString();
//            			var name_with_price = topping_product.display_name + ' x ' + topping_price_str;
//            			topping_list_name.push(name_with_price);
                	}
                }
				
//				var topping_line =  line_id.get_topping_list(true);
//            	if(topping_line.length){
//    				for(var i in topping_line){
//    					var topping_name = topping_line[i].product.display_name;
//    					var topping_x_qty = topping_line[i].quantity/self.orderline.quantity;
//    					if(topping_x_qty > 1){
//    						topping_name = topping_name + ' (x' + topping_x_qty.toString() + ')'
//    					}
//    					var topping_price_fm = self.format_currency_no_symbol(topping_line[i].get_display_price());
//            			var topping_price_str = topping_price_fm.toString();
//            			var name_with_price = topping_name + ' x ' + topping_price_str;
//    					topping_list_name.push(name_with_price);
//    				}
//    			}
//				
//                if(topping_list_name.length){
//            		var topping_name = topping_list_name;
//            		line_id.set_topping_name(topping_name);
//            	}else{
//            		line_id.set_topping_name(false);
//            	}

				line_id.first_qty_input = line_id.quantity;
//				line_id.trigger('change',line_id);
            	order.select_orderline(line_id);
//				this.pos.chrome.screens.products.order_widget.renderElement('scroll');

				//Continue promotion choose if exist
                if(this.is_promotion_product && this.promotion_loop_type != 'none'){
                	if(this.promotion_loop_type == 'multi_product' && this.lists_template_promo && this.promotion_ids && this.promo_line){
                		order.choose_multi_product(this.lists_template_promo,this.promotion_ids,this.promo_line,this.qty_rewared,this.benefit_qty_total);
                	}
					if(this.promotion_loop_type == 'multi_benefit_lines' && this.benefit_lines.length){
						var first_benefit_line = this.benefit_lines[0];
						var template_lists = [];
						var reward_product_tmpls = first_benefit_line.product_ids || [];
						for(var tmpl in reward_product_tmpls){
							var product_template_id = reward_product_tmpls[tmpl];
							var product_template = self.pos.product_templates[product_template_id];
							template_lists.push({
			    				label : product_template.default_code + ' - ' + product_template.name,
			    				item: product_template.id,
			    			});
						}
						_.each(this.promo_line.product_benefit_ids, function(line){
							var benefit_line = self.pos.promo_benefit_lines.filter(function(l){
								return l.id == line && l.allow_additional_price;
							})
							if(benefit_line.length){
								benefit_line = benefit_line[0];
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
						})
						var computed_benefit_qty = first_benefit_line.product_qty*this.promo_line.computed_benefit_qty;
						order.choose_multi_product(template_lists,this.promotion_ids,this.promo_line,this.qty_rewared,computed_benefit_qty, this.benefit_lines);
					}
                	if(this.promotion_loop_type == 'multi_promotion' && this.promotion_ids){
                		order.get_promotion_by_line(this.promotion_ids,this.promotion_ids[0],this.qty_rewared);
                	}
                }
				//Compute promotion
				if(!line_id.combo_id && !this.is_promotion_product){
					order.compute_promotion();
				}
				
				//set discount = 0 when add product combo
				if(line_id.combo_id && order.discount_amount && !order.check_promotion_all_order()){
					order.remove_discount_manual_all_order();
					order.set_discount_amount(0);
				}

				if(this.orderline){
					order.rerender_all_line();
					//rerender when change topping
					if(topping_list_remove.length || topping_list_added.length){
						this.pos.chrome.screens.products.order_widget.renderElement();
					}
				}else{
					this.pos.chrome.screens.products.order_widget.renderElement('scroll');
				}
                return line_id;
            }else{
                return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Sản phẩm không hợp lệ !!!',
                });
            }
//            if (this.options.confirm) {
//                this.options.confirm.call(this);
//            }
        },
        check_default_material: function(material_product_id, option){
			var self = this;				
			if(this.material_list_default.length){
				var material_product = self.pos.db.material_ids[material_product_id];
    			var material_name = material_product.name;
				var material_match = this.material_list_default.filter(function(l){
					return l.option_name.toLowerCase() == material_name.toLowerCase();
				})
				if(material_match.length){
					if(material_match[0].option_type == option){
						if(option != 'normal'){
	        				return true;
	        			}
					}else{
						return false;
					}
				}
			}
        	if(this.orderline && this.orderline.custom_material_list.length){
        		var material_existed = this.orderline.custom_material_list.filter(function(l){
        			return l.option_id == material_product_id && l.option_type == option;
        		})
        		if(material_existed.length){
        			if(option != 'normal'){
        				return true;
        			}
        		}else if(option == 'normal'){
        			return true;
        		}
        	}
        	return false;
        },
		check_option_type: function(domain, type){
			if(!domain.includes(type)){
				return true;
			}else{
				return false;
			}
		}
        
    });
    gui.define_popup({ name: 'topping_poppup', widget:ToppingPopupWidget});

    var ChooseExtraPopupWidget = PopupWidget.extend({
        template: 'ChooseExtraPopupWidget',
        
        show: function(options){
            options = options || {};
			this.orderline = options.orderline || [];
            this._super(options);
//            this.renderElement();
        },
        renderElement: function() {
        	var self = this;
            this._super();
			var lists = $('.item-tr');
			if(lists.length){
				for(var l=1; l< lists.length; l++){
					var valAmount = $(lists[l]).find('.amount-number');
	                if(valAmount.val() == 0) {
	                    continue;
	                }
					self.on_update_qty($(lists[l]).find('.amount-topping'));
				}
			}
            $('.btn-minus').click(function () {
                const _self = $(this);
                let valAmount = _self.parent().find('.amount-number');
                if(valAmount.val() <= 0) {
                    return valAmount.val(0);
                }
                valAmount.val(parseInt(valAmount.val()) - 1);
                self.on_update_qty(_self.parent());
            })
            $('.btn-plus').click(function () {
                const _self = $(this);
                let valAmount = _self.parent().find('.amount-number');
        
                valAmount.val(parseInt(valAmount.val()) + 1);
                self.on_update_qty(_self.parent());
            })
            
        },
        on_update_qty : function(node) {
        	var self = this;
        	var topping_price = node.parent().find('.topping-price').val();
        	var topping_qty = node.find('.amount-number').val();
        	var new_total_price = topping_price*topping_qty;
        	var amount_total_line = node.parent().find('.total-cash-topping');
        	amount_total_line[0].textContent = this.format_currency(new_total_price);
        	
        	var list_topping = this.$el.find('.list-topping-body .item-tr');
        	if(list_topping){
        		var new_price_all = 0;
            	for(var tp = 0; tp <list_topping.length; tp++){
        			var topping_price = list_topping[tp].children[0].value;
            		var topping_qty = list_topping[tp].children[3].children[1].value;
                	var new_total_price = topping_price*topping_qty;
                	new_price_all += new_total_price;
            	}
                	
                var $total = this.el.querySelector('.total-payment > .cash');
                if($total){
                	$total.textContent = this.format_currency(new_price_all);
                }
            }
        },
        click_confirm: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines() 
            this.gui.close_popup();
            var list_topping = this.$el.find('.list-topping-body .item-tr');
        	if(list_topping){
        		var check_topping_change = false;
            	for(var tp = 0; tp <list_topping.length; tp++){
        			var topping_product = list_topping[tp].children[5].value;
            		var topping_qty_choose = list_topping[tp].children[3].children[1].value;
            		var topping_qty = topping_qty_choose*this.orderline.quantity;
            		if(topping_qty > 0){
            			check_topping_change = true;
            			var product = self.pos.db.get_product_by_id(topping_product);
            			var topping_line = orderlines.filter(function(tp_line) 
        					{return tp_line.is_topping_line && tp_line.related_line_id == self.orderline.id && tp_line.product.id == product.id;}
        	    		);
            			if(topping_line.length){
//            				var new_qty = topping_line[0].quantity + topping_qty;
							if(topping_line[0].quantity != topping_qty){
								topping_line[0].set_quantity(topping_qty, true);
							}
            			}else{
            				order.add_product(product,{
                                quantity:topping_qty,
                                merge:false,
								disable_selected:true,
                                extras: {related_line_id:self.orderline.id,
    	                    		 	 is_topping_line:true}
                            });
            			}
            		}else{
						var product = self.pos.db.get_product_by_id(topping_product);
						var topping_line = orderlines.filter(function(tp_line) 
        					{return tp_line.is_topping_line && tp_line.related_line_id == self.orderline.id && tp_line.product.id == product.id;}
        	    		);
						if(topping_line){
							check_topping_change = true;
		                	order.orderlines.remove(topping_line);
		                }
					}
            	}
            	if(check_topping_change){
//            		var topping_list_name = [];
//	            	var topping_line = orderlines.filter(function(tp_line) 
//    					{return tp_line.is_topping_line && tp_line.related_line_id == self.orderline.id;}
//    	    		);
//	            	if(topping_line.length){
//        				for(var i in topping_line){
//        					var topping_name = topping_line[i].product.display_name;
//        					var topping_x_qty = topping_line[i].quantity/self.orderline.quantity;
//        					if(topping_x_qty > 1){
//        						topping_name = topping_name + ' (x' + topping_x_qty.toString() + ')'
//        					}
//        					var topping_price_fm = self.format_currency_no_symbol(topping_line[i].get_display_price());
//                			var topping_price_str = topping_price_fm.toString();
//                			var name_with_price = topping_name + ' x ' + topping_price_str;
//        					topping_list_name.push(name_with_price);
//        				}
//        			}
//	            	if(topping_list_name.length){
//	            		var topping_name = topping_list_name;
//	            		self.orderline.set_topping_name(topping_name);
//	            	}
            		self.orderline.trigger('change',self.orderline);
        			order.select_orderline(self.orderline);
            	}
            }
        },
		get_topping_current_qty: function(topping_id){
			var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines();
			var qty = 0;
			var topping_line = orderlines.filter(function(tp_line) 
				{return tp_line.is_topping_line && tp_line.related_line_id == self.orderline.id && tp_line.product.id == topping_id;}
			);
			if(topping_line.length){
				var qty = topping_line[0].quantity/self.orderline.quantity;
			}
			return qty;
		}
    });
    gui.define_popup({ name: 'extra_topping', widget:ChooseExtraPopupWidget});
    
    var VoucherInputPopupWidget = PopupWidget.extend({
        template: 'VoucherInputPopupWidget',
        
        show: function(options){
            options = options || {};
            var self = this;
            var order = this.pos.get_order();
            var amount_total = order.get_total_with_tax();
            var amount = amount_total - order.get_total_paid();
            this._super(options);
            this.popup_voucher = true;
            this.code_list = options.code_list || [];
            this.code_list_char = '';
            this.change_amount = 0;
            if(this.code_list.length){
            	var code_list_name = [];
            	var total_voucher_amount = 0;
            	for(var i in this.code_list){
            		code_list_name.push(this.code_list[i][1]);
            		total_voucher_amount += this.code_list[i][0];
            	}
            	if(total_voucher_amount > amount){
            		this.change_amount = total_voucher_amount - amount;
            	}
            	this.code_list_char = code_list_name.join(', ');
            }
            this.cashregister = options.cashregister || false;

            this.renderElement();
            $('.check-voucher').click(function () {
                self.show_popup_voucher();
            })
            $('.confirm-voucher').click(function () {
                self.click_confirm_voucher();
            })
            var value = this.$('input,textarea').val();
//            this.$('input,textarea').focus().val('').val(value);
        },
        
        show_popup_voucher: function(code=false){
        	var self = this;
        	var value = this.$('input,textarea').val();
        	if(value && !code){
        		code = value;
        	}
        	var voucher_amount = 0;
        	var order = this.pos.get_order()
        	var lines = order.get_paymentlines();
    		if(!order.orderlines.length){
    			return true;
    		}
    		var check_dupp_code = false;
    		for(var i=0; i<this.code_list.length; i++){
    			if(this.code_list[i][1] && this.code_list[i][1] == code){
    				check_dupp_code = true;
    				break;
    			}
    		}
    		for(var i=0; i<lines.length; i++){
    			if(lines[i].voucher_code && lines[i].voucher_code == code){
    				check_dupp_code = true;
    				break;
    			}
    		}
    		if(check_dupp_code){
    			return self.gui.show_popup('voucherinput',{
        	    	title: 'Nhập mã Voucher để thanh toán',
        	    	value: value,
        	    	state: 'error',
        	    	code_list: self.code_list,
        	    	cashregister:self.cashregister,
        	    	error: 'Voucher ' + code + ' đã được nhập !!',
    			})
    		}
    		
    		var voucher_code = ({code:code});
    		var search_type = 'voucher';
			var backend_id = self.pos.config.warehouse_id
			
			rpc.query({
                model: 'sale.promo.header',
                method: 'check_coupon_apply',
                args: [voucher_code,search_type,backend_id[0]],
            }).then(function(result_from_server){
            	var error = '';
            	var result_from_server = result_from_server;
				if (!result_from_server.length){
					error = 'Mã Voucher không tồn tại. Vui lòng kiểm tra lại';
				}
				if (result_from_server[0]=='date'){
					error = 'Voucher đã hết hạn (' + result_from_server[1] + '), Vui lòng kiểm tra lại !!';
				}
				if (result_from_server[0]=='count'){
					error =  ['Mã Voucher đã được sử dụng ở',
							  'Đơn hàng: ' + result_from_server[2],
							  'CH sử dụng: ' + result_from_server[3] || '',
							  'Ngày giờ: ' + result_from_server[4]]
				}
				if(error == ''){
					var recheck_dupp_code = false;
		    		for(var i=0; i<self.code_list.length; i++){
		    			if(self.code_list[i][1] && self.code_list[i][1] == code){
		    				recheck_dupp_code = true;
		    				break;
		    			}
		    		}
		    		if(!recheck_dupp_code){
		    			self.code_list.push([result_from_server[0],voucher_code.code]);
		    		}
					self.gui.show_popup('voucherinput',{
		    	    	title: 'Nhập mã Voucher để thanh toán',
		    	    	state: 'success',
		    	    	code_list: self.code_list,
						cashregister:self.cashregister,
						voucher_publish_name:result_from_server[2].toUpperCase()
	    			})
				}else{
					self.gui.show_popup('voucherinput',{
		    	    	title: 'Nhập mã Voucher để thanh toán',
		    	    	value: value,
		    	    	state: 'error',
		    	    	code_list: self.code_list,
		    	    	cashregister:self.cashregister,
		    	    	error: error,
	    			})
				}
	        },function(error){
				error.event.preventDefault();
				self.gui.show_popup('error',{
	                'title': _t('Error: Could not Save Changes'),
	                'body': _t('Your Internet connection is probably down.'),
	            });
	        });
        },
        
        click_confirm_voucher: function(){
        	var self = this;
        	var value = this.$('input,textarea').val();
        	var order = this.pos.get_order();
            var code_list = this.code_list;
			var lines = order.get_paymentlines();
            this.gui.close_popup();
            if(!code_list.length){
    			return this.gui.show_popup('voucherinput',{
	    	    	title: 'Nhập mã Voucher để thanh toán',
	    	    	value: value,
	    	    	state: 'error',
	    	    	error: 'Không có mã Voucher hợp lệ',
	    	    	cashregister:self.cashregister,
    			})
    		}
            for(var i in code_list){
            	var voucher_code = code_list[i];

				var check_dupp_code = false;
	    		for(var i=0; i<lines.length; i++){
	    			if(lines[i].voucher_code && lines[i].voucher_code == voucher_code[1]){
	    				check_dupp_code = true;
	    				break;
	    			}
	    		}
	    		if(check_dupp_code){
	    			return self.gui.show_popup('voucherinput',{
	        	    	title: 'Nhập mã Voucher để thanh toán',
	        	    	value: value,
	        	    	state: 'error',
	        	    	code_list: self.code_list,
	        	    	cashregister:self.cashregister,
	        	    	error: 'Voucher ' + voucher_code[1] + ' đã được nhập !!',
	    			})
	    		}

				order.add_paymentline(this.cashregister);
				var total_to_paid = order.get_total_with_tax() - order.get_total_paid();
				if (total_to_paid == 0 && voucher_code[0] >= self.change_amount){
					order.selected_paymentline.set_amount(voucher_code[0] - self.change_amount);
					self.change_amount = 0;
				}else if(voucher_code[0] > total_to_paid){
					order.selected_paymentline.set_amount(total_to_paid);
				} else{
					order.selected_paymentline.set_amount(voucher_code[0]);
				}
				order.selected_paymentline.set_voucher_code(voucher_code[1]);
				order.selected_paymentline.set_voucher_max_value(voucher_code[0]);
            }
			order.use_coupon = true;
			order.trigger('change', order);
    		self.pos.chrome.screens.payment.sort_payment_line();
			self.pos.chrome.screens.payment.show();
        },
        
        click_confirm: function(){
        	var self = this;
        	self.show_popup_voucher();
        }
        
    });
    gui.define_popup({name:'voucherinput', widget: VoucherInputPopupWidget});
    
    var EmployeeCouponAlertPopupWidget = PopupWidget.extend({
        template:'EmployeeCouponAlertPopupWidget',
    });
	gui.define_popup({name:'employee-coupon-alert', widget: EmployeeCouponAlertPopupWidget});
	
    var NumberPopupWidgetNoPlus = PopupWidget.extend({
		template: 'NumberPopupWidgetNoPlus',
		show: function(options){
			options = options || {};
			this._super(options);
	
			this.inputbuffer = '' + (options.value   || '');
			this.renderElement();
			this.firstinput = true;
		},
		format_value: function(value,decimals){
			if (typeof value =='string'){
				value = value.replace(/,/g,'');
			}
			var nStr = value;
			nStr += '';
			var x = nStr.split('.');
			var x1 = x[0];
			var x2 = x.length > 1 ? '.' + x[1] : '';
			var rgx = /(\d+)(\d{3})/;
			while (rgx.test(x1)) {
				x1 = x1.replace(rgx, '$1' + ',' + '$2');
			}
			if ( decimals == 0 ){
				return x1;
			}else{
				return x1 + x2;
			}
		},
		click_numpad: function(event){
			var newbuf = this.gui.numpad_input(
				this.inputbuffer, 
				$(event.target).data('action'), 
				{'firstinput': this.firstinput});
			newbuf = newbuf.replace(/,/g,'');
			this.firstinput = (newbuf.length === 0);
			
			if (newbuf !== this.inputbuffer) {
				this.inputbuffer = newbuf;
				this.$('.value').text(this.format_value(this.inputbuffer));
			}
		},
		
		click_confirm: function(){
			this.gui.close_popup();
			if(this.inputbuffer && this.inputbuffer != '0'){
				if( this.options.confirm ){
					this.options.confirm.call(this,this.inputbuffer);
				}
				var order = this.pos.get_order();
	            order.rerender_all_line();
			}
		},
	});
	
	gui.define_popup({name:'numberinputwidgetnoplus', widget: NumberPopupWidgetNoPlus});
	
	var TextInputPopupWidget = PopupWidget.extend({
		template: 'TextInputPopupWidget',
		
		show: function(options){
			options = options || {};
			this._super(options);
			this.popup_coupon = true;
			this.renderElement();
			if(!options.off_focus){
				this.$('input,textarea').focus();
			}
		},
		
		click_confirm: function(){
			var value = this.$('input,textarea').val();
			this.gui.close_popup();
			if( this.options.confirm ){
				this.options.confirm.call(this,value);
			}
		},
	});
	gui.define_popup({name:'textinput', widget: TextInputPopupWidget});
	
	var InvoiceInfoInputPopupWidget = PopupWidget.extend({
		template: 'InvoiceInfoInputPopupWidget',
		
		show: function(options){
			options = options || {};
			this._super(options);
			this.renderElement();
			if(!options.off_focus){
				this.$('input.name').focus();
			}
			var order = this.pos.get_order();
			this.$('textarea.contact').val(order.invoice_contact)
		},
		
		click_confirm: function(){
			var order = this.pos.get_order();
			if(!this.$('input.name').val() || !this.$('input.vat').val() || !this.$('input.email').val() || !this.$('input.address').val() || !this.$('textarea.contact').val()){
				var error_mess = this.$el.find('.invoice-error-mess')[0];
            	error_mess.textContent  = "Vui lòng nhập đủ các thông tin bắt buộc";
				return;
			}
			this.gui.close_popup();
			order.invoice_name = this.$('input.name').val();
			order.invoice_vat = this.$('input.vat').val();
			order.invoice_address = this.$('input.address').val();
			order.invoice_email = this.$('input.email').val();
			order.invoice_contact = this.$('textarea.contact').val();
			order.invoice_note = this.$('input.note').val();
			order.invoice_request = true;
			order.trigger('change', order);
		},
	});
	gui.define_popup({name:'invoiceinfoinput', widget: InvoiceInfoInputPopupWidget});
	
	var SelectionWarehousePopupWidget = PopupWidget.extend({
	    template: 'SelectionWarehousePopupWidget',
	    events: {
	    	'click .title': 'clear_search',
	        'click .button.cancel':  'click_cancel',
	        'click .button.confirm': 'clear_search',
	        'click .selection-item': 'click_item',
	    },
	    init: function(parent, args) {
	    	var self = this;
	        this._super(parent, args);
	        this.options = {};
	        this.clear_search_handler = function(event){
	            self.clear_search();
	        };
	        var search_timeout  = null;
	        this.search_handler = function(event){
	            if(event.type == "keypress" || event.keyCode === 46 || event.keyCode === 8){
	                clearTimeout(search_timeout);
	
	                var searchbox = this;
	
	                search_timeout = setTimeout(function(){
	                    self.perform_search(searchbox.value);
	                },70);
	            }
	        };
	    },
		show: function(options){
	        var self = this;
	        options = options || {};
	        this._super(options);
	
	        this.list = options.list || [];
	        this.is_selected = options.is_selected || function (item) { return false; };
	        this.renderElement();
	    },
	    click_item : function(event) {
	        this.gui.close_popup();
	        if (this.options.confirm) {
	            var item = this.list[parseInt($(event.target).data('item-index'))];
	            item = item ? item.item : item;
	            this.options.confirm.call(self,item);
	        }
	    },
	    renderElement: function(){
	        this._super();
	        this.el.querySelector('.searchbox input').addEventListener('keypress',this.search_handler);
	        this.el.querySelector('.searchbox input').addEventListener('keydown',this.search_handler);
	        this.el.querySelector('.search-clear').addEventListener('click',this.clear_search_handler);
	        var input = this.el.querySelector('.searchbox input');
	        input.focus();
	    },
	 	// empties the content of the search box
	    clear_search: function(){
	        var input = this.el.querySelector('.searchbox input');
	        input.value = '';
	        input.focus();
	    },
	    perform_search: function(query){
			var self = this;
	        var warehouses;
			this.list = [];
	        if(query){
	            warehouses = this.pos.db.search_warehouse(this.pos.warehouse_ids.length ,query);
	        }else{
				warehouses = this.pos.warehouse_ids;
			}
			_.each(warehouses, function(wh){
                self.list.push({
                    label : wh.code + ' - ' + wh.display_name,
                    item: wh,
                });
            });
	        this.renderElement();
	        var input = this.el.querySelector('.searchbox input');
	        input.value = query;
	        input.focus();
	    },
	    click_confirm:function(){
	    	var input = this.el.querySelector('.searchbox input');
	    	this.perform_search(input.value);
	    },
	});
	gui.define_popup({name:'selection_warehouse', widget: SelectionWarehousePopupWidget});
	
});
    