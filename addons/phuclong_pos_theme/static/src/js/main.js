odoo.define('phuclong_pos_theme.templates', function (require) {
    "use strict";
    var screens = require('point_of_sale.screens');
	var chrome = require('point_of_sale.chrome');
    var core = require('web.core');
    var QWeb     = core.qweb;
    var _t = core._t;
    var gui = require('point_of_sale.gui');
    var rpc = require('web.rpc');
    var BarcodeReader = require('point_of_sale.BarcodeReader');
//    var return_screen = require('fe_pos_return_product.fe_pos_return_product');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    var session = require('web.session');
    var field_utils = require('web.field_utils');
    var models = require('point_of_sale.models');
    // Thai: Sửa icon loading trên POS
    var blockUI = require('web.framework');
    var Widget = require('web.Widget');
    var throbbers = [];
    var clearTimeout_vals = null;
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;
    var messages_by_seconds = function() {
        return [
            [0, _t("Loading...")],
            [20, _t("Still loading...")],
            [60, _t("Still loading...<br />Please be patient.")],
            [120, _t("Don't leave yet,<br />it's still loading...")],
            [300, _t("You may not believe it,<br />but the application is actually loading...")],
            [420, _t("Take a minute to get a coffee,<br />because it's loading...")],
            [3600, _t("Maybe you should consider reloading the application by pressing F5...")]
        ];
    };
    var ThrobberCustom = Widget.extend({
        template: "ThrobberCustom",
        start: function() {
            this.start_time = new Date().getTime();
            this.act_message();
        },
        act_message: function() {
            var self = this;
            setTimeout(function() {
                if (self.isDestroyed())
                    return;
                var seconds = (new Date().getTime() - self.start_time) / 1000;
                var mes;
                _.each(messages_by_seconds(), function(el) {
                    if (seconds >= el[0])
                        mes = el[1];
                });
                self.$(".oe_throbber_message").html(mes);
                self.act_message();
            }, 1000);
        },
    });
    var Throbber = Widget.extend({
        template: "Throbber",
        start: function() {
            this.start_time = new Date().getTime();
            this.act_message();
        },
        act_message: function() {
            var self = this;
            setTimeout(function() {
                if (self.isDestroyed())
                    return;
                var seconds = (new Date().getTime() - self.start_time) / 1000;
                var mes;
                _.each(messages_by_seconds(), function(el) {
                    if (seconds >= el[0])
                        mes = el[1];
                });
                self.$(".oe_throbber_message").html(mes);
                self.act_message();
            }, 1000);
        },
    });
    blockUI.blockUI = function(){
        var tmp = $.blockUI.apply($, arguments);
        if ($('pos .pos_content')){
            var throbber = new ThrobberCustom();
        } else{
            var throbber = new Throbber();
        }
        throbbers.push(throbber);
        throbber.appendTo($(".oe_blockui_spin_container"));
        $(document.body).addClass('o_ui_blocked');
        return tmp;
    }
    
    screens.ProductCategoriesWidget.include({
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            this.combo = false;
            this.switch_combo_handler = function(combo){
                var combo_id = combo.target.dataset.comboId;
                var combo_obj = self.pos.db.get_combo_by_id(combo_id);
				self.combo = combo_obj;
                if (combo_obj.use_for_coupon){
                    self.renderElement(true, combo_id);
                } else{
                    self.renderElement(true, false);
                }
                self.set_combo(combo_id);
            };
        },
        set_combo : function(combo_id){
            $('.combo-item').removeClass('combo-actived');
            var list_combo = this.pos.db.list_combo;
            var combo = false;
            if(list_combo){
            	combo = list_combo.filter(function(item){
                    return item.id == combo_id})
            }
            
            if(combo_id){
                this.combo = combo ? combo[0]:false;
                
                $('a[data-combo-id='+combo_id+']').addClass('combo-actived');
            }
            else{
                this.combo = false;
            }
        },
        renderElement: function(show_combo=false, combo_coupon_id=false, render_from_combo_button=false){
            var el_str  = QWeb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
			var old_el = this.el.innerHTML;
    		
            el_node.innerHTML = el_str;
            el_node = el_node.childNodes[1];
			var check_rerender = true;    		
			if(((this.category && this.category.parent_id) || this.combo) && old_el && !render_from_combo_button){
	            el_node = this.el;
				check_rerender = false;
    		}else{
				if(this.el && this.el.parentNode){
	                this.el.parentNode.replaceChild(el_node,this.el);
	            }
				this.el = el_node;
			}
			
			var list_container = el_node.querySelector('.category-list');

			var numpad = this.pos.chrome.screens.products.numpad;
			var withpics = this.pos.config.iface_display_categ_images;
			if (list_container && check_rerender) { 
                if (!withpics) {
                    list_container.classList.add('simple');
                } else {
                    list_container.classList.remove('simple');
                }
                if(show_combo){
                    // render Combo
                    var order_sale_type = this.pos.get_order().sale_type_id;
                    var combo_w_sale_type = this.pos.db.list_combo.filter(function(item){
						return !item.sale_type_ids.length || item.sale_type_ids.indexOf(order_sale_type)>=0;
					});
                    for(var i = 0, len = combo_w_sale_type.length; i < len; i++){
                    	//Vuong: render combo by 1 conbo for coupon
                    	var combo = combo_w_sale_type[i];
                    	if(combo_coupon_id){
                    		if(combo.id == combo_coupon_id){
                    			list_container.appendChild(this.render_combo(combo,true));
                    			break;
                    		}
                    	}else{
                    		if(combo.use_for_coupon == false){
                        		list_container.appendChild(this.render_combo(combo));
                        	}
                    	}
                    }
					numpad.block_ui_on_use_combo(true);
                } else{
					for(var i = 0, len = this.subcategories.length; i < len; i++){
                        list_container.appendChild(this.render_category(this.subcategories[i],withpics));
                    }
					numpad.block_ui_on_use_combo(false);
                }
            }
            
            var buttons = el_node.querySelectorAll('.js-category-switch');
            
            for(var i = 0; i < buttons.length; i++){
                buttons[i].addEventListener('click',this.switch_category_handler);
                
            }
            if(show_combo){
                var products = []
                var products_ids = this.pos.db.get_product_by_combo(this.combo.id, this.pos.get_order());
                for(var i=0;i<products_ids.length;i++){
                    if(this.pos.db.product_by_id[products_ids[i]]){
						products.push(this.pos.db.product_by_id[products_ids[i]]);
//                        var order_lines = this.pos.get_order() ? this.pos.get_order().orderlines : [];
//                        if (order_lines){
//                            var is_selected_product = order_lines.models.filter(function(item){
//                                return item.product.id == products_ids[i] && item.combo_id && item.is_done_combo == false;
//                            })
//                            if(is_selected_product.length == 0){
//                                products.push(this.pos.db.product_by_id[products_ids[i]]);
//                            }
//                        } else{
//                            products.push(this.pos.db.product_by_id[products_ids[i]]);
//                        }
                    }
                }
            } else{
                var products = this.pos.db.get_product_by_category(this.category.id); 
                this.set_combo(false);
            }
            products = products.filter(function(item){return item.default_code != 'reward_code'});
            this.product_list_widget.set_product_list(products); // FIXME: this should be moved elsewhere ...
    
            this.el.querySelector('.searchbox input').addEventListener('keypress',this.search_handler);
    
            this.el.querySelector('.searchbox input').addEventListener('keydown',this.search_handler);
    
            this.el.querySelector('.search-clear.right').addEventListener('click',this.clear_search_handler);
    		
            if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
                this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
            }
//			$('.handle-tab').click(function () {
//                const _self = $(this);
//                $('.handle-tab').removeClass('active show');
//                _self.tab('show');
//            })
            var $carousel_1 = $('.custom-carousel-1').owlCarousel({
                loop: false,
                margin: 5,
                nav: true,
                dots: false,
                autoWidth:true,
                items: 1,
                responsiveClass:true,
                navText: ['<img src="/phuclong_pos_theme/static/src/img/w_arrow_left.png" />','<img src="/phuclong_pos_theme/static/src/img/w_arrow_right.png" />'],
                responsive: {
                    0: {
                        items: 1
                    },
        
                    1024: {
                        items: 1
                    },
        
                    1375: {
                        items: 1
                    }
                }
            })
			if(check_rerender){
				$('.custom-carousel-2').owlCarousel({
		                loop: false,
		                margin: false,
		                nav: true,
		                dots: false,
		                items: 1,
		                autoWidth:true,
		                navText: ['<img src="/phuclong_pos_theme/static/src/img/w_arrow_left.png" />','<img src="/phuclong_pos_theme/static/src/img/w_arrow_right.png" />'],
	            })
			}
			
			$('.wrap-center-menu .owl-next').click(function() {
                refreshCarousel();
            })
            $('.wrap-center-menu .owl-prev').click(function() {
                refreshCarousel();
            })
            
            function refreshCarousel() {
                $carousel_1.data('owl.carousel')._invalidated.width = true;
                $carousel_1.trigger('refresh.owl.carousel');
            };
            
            var nav = $('#tabProduct .owl-nav');
            var tabProduct = $('#tabProduct');
//			var nav_disabled = $('.disabled.owl-nav');
//			if(nav_disabled) {
//                nav_disabled.removeClass('disabled');
//            } 
//            tabProduct.addClass('has-nav');
            if(nav.hasClass('disabled')) {
                tabProduct.removeClass('has-nav');
            } else {
                tabProduct.addClass('has-nav');
            }
        },
        render_combo: function(combo, combo_actived=false){
            var combo_html = QWeb.render('ComboSimpleButton',{ 
                widget:  this, 
                combo: combo, 
                actived: combo_actived
                });
                combo_html = _.str.trim(combo_html);
            var combo_node = document.createElement('div');
                combo_node.innerHTML = combo_html;
                combo_node = combo_node.childNodes[0];
            combo_node.addEventListener('click',this.switch_combo_handler);
            return combo_node;
        },
		// changes the category. if undefined, sets to root category
	    set_category : function(category){
			$('.category-simple-button').removeClass('category-actived');
	        var db = this.pos.db;
	        if(!category){
	            this.category = db.get_category_by_id(db.root_category_id);
	        }else{
	            this.category = category;
	        }
	        this.breadcrumb = [];
	        var ancestors_ids = db.get_category_ancestors_ids(this.category.id);
	        for(var i = 1; i < ancestors_ids.length; i++){
	            this.breadcrumb.push(db.get_category_by_id(ancestors_ids[i]));
	        }
	        if(this.category.id !== db.root_category_id){
	            this.breadcrumb.push(this.category);
	        }
			if(!this.category.parent_id){
				this.subcategories = db.get_category_by_id(db.get_category_childs_ids(this.category.id));
			}else{
				$('a[data-category-id='+this.category.id+']').addClass('category-actived');
			}
	    },
		perform_search: function(category, query, buy_result){
	    	var self = this;
	        var products;
	        var order = this.pos.get_order();
	        if(query){
	        	var employee = self.pos.employee_by_barcode[query] || false;
	        	var partner = self.pos.db.partner_by_barcode[query] || false;
				if(employee){
					order.set_saleman(employee.id);
					this.clear_search();
				}else if(partner){
					order.set_client(partner);
					this.clear_search();
				}else{
					if(self.combo){
			        	var products_ids_in_combo = this.pos.db.get_product_by_combo(self.combo.id, order);
			            var products_no_limits = this.pos.db.search_product_in_category_no_limit(0,query);
						products = products_no_limits.filter(function(p){
							return products_ids_in_combo.includes(p.id);
						})
					}else{
						products = this.pos.db.search_product_in_category(category.id,query);
					}
//		            if(buy_result && products.length === 1){
//		                    this.pos.get_order().add_product(products[0]);
//		                    this.clear_search();
//		            }else{
	                this.product_list_widget.set_product_list(products);
//		            }
				}
	        }else{
				if(self.combo){
		        	var products = [];
					var products_in_combo = this.pos.db.get_product_by_combo(self.combo.id, order);
					_.each(products_in_combo, function(product){
						var product_obj = self.pos.db.get_product_by_id(product);
						if(product_obj){
							products.push(self.pos.db.get_product_by_id(product));
						}
					})
				}else{
					products = this.pos.db.get_product_by_category(this.category.id);
				}
	            this.product_list_widget.set_product_list(products);
	        }
	    },
		clear_search: function(){
			var self = this;
			var order = this.pos.get_order();
			if(self.combo){
	        	var products = [];
				var products_in_combo = this.pos.db.get_product_by_combo(self.combo.id, order);
				_.each(products_in_combo, function(product){
					var product_obj = self.pos.db.get_product_by_id(product);
					if(product_obj){
						products.push(self.pos.db.get_product_by_id(product));
					}
				})
			}else{
				var products = this.pos.db.get_product_by_category(this.category.id);
			}
	        this.product_list_widget.set_product_list(products);
	        var input = this.el.querySelector('.searchbox input');
	            input.value = '';
	            input.focus();
	    },
    });
    screens.ProductScreenWidget.include({
        _onKeypadKeyDown: function (ev) {
            //prevent input and textarea keydown event
            if(!_.contains(["INPUT", "TEXTAREA"], $(ev.target).prop('tagName')) && !this.gui.current_popup) {
                clearTimeout(this.timeout);
                this.buffered_key_events.push(ev);
                this.timeout = setTimeout(_.bind(this._handleBufferedKeys, this), BarcodeEvents.max_time_between_keys_in_ms);
            }
        },
        click_product: function(product) {
            var self = this;
            var order = this.pos.get_order();
			if (!order.saleman_id && this.pos.config.use_pos_saleman == true){
				  return this.gui.show_popup('alert',{
		              'title': 'ERROR',
		              'body':  'Chưa nhập Nhân viên bán hàng !!!',
		          });
		    }
            var combo = this.pos.chrome.screens.products.product_categories_widget.combo;
            var combo_id = combo ? combo.id : false
            var line_in_other_combo = order.orderlines.models.filter(function(line){
                return line.is_done_combo == false && line.combo_id && line.combo_id != combo_id});
            if (line_in_other_combo.length > 0){
                self.gui.show_popup('confirm',{
                    'title': _t('Combo chưa hoàn thành! Bạn muốn đổi thành combo khác chứ?'),
                    'body': _t('Nếu xác nhận đổi thành combo khác, hệ thống sẽ tự động xóa những sản phẩm thuộc các combo chưa hoàn thành'),
                    confirm: function(){
                        if(!self.pos.config.permission_destroy_line){
                            _.each(line_in_other_combo, function(line){
                                order.remove_orderline(line);
                            })
                            if(product.to_weight && this.pos.config.iface_electronic_scale){
                                self.gui.show_screen('scale',{product: product});
                            }else{
                                return self.pos.chrome.gui.show_popup('topping_poppup',{
                                    'product': product,
                                });
                            }
                        } else{
                            var list_rules = [];
                            _.each(self.pos.rules, function(rule){
                                list_rules.push({
                                    label : rule.name,
                                    item: rule,
                                });
                            });
                            self.pos.chrome.gui.show_popup('selection',{
                                'title': _t('Chọn người có quyền ?'),
                                'list': list_rules,
                                'confirm':function(rule){
                                    self.pos.chrome.gui.show_popup('passtextinputwidget',{
                                        'title': _t('Password ?'),
                                        confirm: function(pw) {
                                            if (pw == rule.destroy_order_password){
                                                _.each(line_in_other_combo, function(line){
                                                    order.remove_orderline(line);
                                                })
                                                if(product.to_weight && this.pos.config.iface_electronic_scale){
                                                    self.gui.show_screen('scale',{product: product});
                                                }else{
                                                    return self.pos.chrome.gui.show_popup('topping_poppup',{
                                                        'product': product,
                                                    });
                                                }
                                            }else{
                                                self.gui.show_popup('error',_t('Sai mật khẩu !'));
                                            }
                                        }
                                    });
                                },
                            });
                        }
                        
                        
                    },
                });
            } else{
                if(product.to_weight && this.pos.config.iface_electronic_scale){
                    self.gui.show_screen('scale',{product: product});
                }else{
                    return self.pos.chrome.gui.show_popup('topping_poppup',{
                        'product': product,
                    });
                }
            }
        },
    });
    screens.ProductListWidget.include({
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.product_has_promo = this.product_in_promo || [];
            this.categ_has_combo = this.categ_has_combo || [];
            this.product_has_combo = this.product_in_combo || [];
            this.set_product_has_promo();
        },
        set_product_has_promo: function(){
            var self = this;
            var now = new Date();
            now.format("yy/M/dd");
            var hours = now.getHours();
            var minute = now.getMinutes();
            var float_now = hours + minute/60;
            var apply_any_time = false;
            var all_promotion_lines = []
            for (var i = 0; i< this.pos.promotion_header.length;i++){
                var header = this.pos.promotion_header[i];
                if(header.use_for_coupon){
                    continue;
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
                                if(promo_line_id[0].product_attribute !='order'){
                                    all_promotion_lines.push(promo_line_id[0]);
                                }
                            }
                        }
                    });
                }
            }
            _.each(all_promotion_lines, function(item){
                if(item.product_attribute == 'cat'){
                    var cat_dom = item.categories_dom;
                    var cat_dom_arr = cat_dom.replace('[','').replace(']','').split(',');
                    for(var i =0;i<cat_dom_arr.length;i++){
                        if (self.categ_has_combo.indexOf(parseInt(cat_dom_arr[i])) < 0){
                            self.categ_has_combo.push(parseInt(cat_dom_arr[i]));
                        }
                    }
                }
                if(item.product_attribute == 'combo'){
                    for(var i =0;i<item.product_ids.length;i++){
                        if (self.product_has_promo.indexOf(parseInt(item.product_ids[i])) < 0){
                            self.product_has_promo.push(parseInt(item.product_ids[i]));
                        }
                    }
                }
                if(item.product_attribute == 'product_template'){
                    if (self.product_has_promo.indexOf(parseInt(item.product_tmpl_id[0])) < 0){
                        self.product_has_promo.push(parseInt(item.product_tmpl_id[0]));
                    }
                }
            })
            var combos = this.pos.db.list_combo;
            _.each(combos, function(combo){
                var products = self.pos.db.get_product_by_combo(combo.id);
                _.each(products, function(item){
                    if (self.product_has_combo.indexOf(item) < 0){
                        self.product_has_combo.push(item);
                    }
                })
            })
        },
    });
    screens.NumpadWidget.include({
        delete_orderline: function(){
            var self = this;
            var order = this.pos.get_order();
            var selected_orderline = order.get_selected_orderline();
            if(!selected_orderline){
                return;
            }
            if(selected_orderline.is_promotion_line){
                return self.gui.show_popup('alert',{
                      'title': 'ERROR',
                      'body':  'Bạn không có quyền điều chỉnh hàng khuyến mãi !',
                });
            }
            if(!this.pos.config.permission_destroy_line){
                if(selected_orderline.is_done_combo == true){
                    self.gui.show_popup('confirm',{
                        'title': _t('Cảnh báo'),
                        'body': _t('Toàn bộ Combo này sẽ bị xoá. Bạn có muốn tiếp tục xoá?'),
                        confirm: function(){
                            var orderlines = order.orderlines.models;
                            order.log_history_permisson('destroy_order_line', false, false, selected_orderline.product.id);
                            var commbo_line_2_delete = orderlines.filter(function(item){
                                return item.combo_id == selected_orderline.combo_id && item.is_done_combo == true && item.combo_seq == selected_orderline.combo_seq;
                            })
							if(commbo_line_2_delete.length){
								var header_node = commbo_line_2_delete[0].node.previousElementSibling;
								if(header_node && !$(header_node).hasClass('orderline')){
									header_node.parentNode.removeChild(header_node);
								}
							}
                            _.each(commbo_line_2_delete, function(item){
								//remove promotion topping
								var topping_line =  item.get_topping_list(true);
					        	if(topping_line.length){
									for(var i in topping_line){
										var recompute_promotion_id = topping_line[i].promotion_line_id ? topping_line[i].promotion_line_id : topping_line[i].promotion_line_temp_id;
			                            if(recompute_promotion_id){
			                                order.reset_promotion_line_no_render(recompute_promotion_id);
			                            }
									}
								}
                                order.remove_orderline(item);
                            })
							var recompute_promotion_id = selected_orderline.promotion_line_id ? selected_orderline.promotion_line_id : selected_orderline.promotion_line_temp_id;
                            if(recompute_promotion_id){
                                order.reset_promotion_line_no_render(recompute_promotion_id);
                            }
							
                            order.compute_promotion();
							order.rerender_all_line();
//							this.pos.chrome.screens.products.order_widget.renderElement('scroll');
                        }
                    })
                } else{
                	order.log_history_permisson('destroy_order_line', false, false, selected_orderline.product.id);
                    order.remove_orderline(selected_orderline);
					var recompute_promotion_id = selected_orderline.promotion_line_id ? selected_orderline.promotion_line_id : selected_orderline.promotion_line_temp_id;
                    if(recompute_promotion_id){
                        order.reset_promotion_line_no_render(recompute_promotion_id);
                    }
                    order.compute_promotion();
        //			order.checked_promotion = false;
					order.rerender_all_line();
//					this.pos.chrome.screens.products.order_widget.renderElement('scroll');
                    return;
                }
            } else{
                var list_rules = [];
                _.each(self.pos.rules, function(rule){
                    list_rules.push({
                        label : rule.name,
                        item: rule,
                    });
                });
                if(selected_orderline.is_done_combo == true){
                    self.gui.show_popup('confirm',{
                        'title': _t('Cảnh báo'),
                        'body': _t('Toàn bộ Combo này sẽ bị xoá. Bạn có muốn tiếp tục xoá?'),
                        confirm: function(){
                            self.gui.show_popup('selection',{
                                'title': _t('Chọn người có quyền ?'),
                                'list': list_rules,
                                'confirm':function(rule){
                                    self.gui.show_popup('passtextinputwidget',{
                                        'title': _t('Password ?'),
                                        confirm: function(pw) {
                                            if (pw == rule.destroy_order_password){
                                            	order.log_history_permisson('destroy_order_line', rule.id, false, selected_orderline.product.id);
                                                order.remove_orderline(selected_orderline);
                                                //Thai: Xóa các sản phẩm thuộc cùng Combo
                                                var orderlines = order.orderlines.models;
                                                var commbo_line_2_delete = orderlines.filter(function(item){
                                                    return item.combo_id == selected_orderline.combo_id && item.is_done_combo == true && item.combo_seq == selected_orderline.combo_seq;
                                                })
												if(commbo_line_2_delete.length){
													var header_node = commbo_line_2_delete[0].node.previousElementSibling;
													if(header_node && !$(header_node).hasClass('orderline')){
														header_node.parentNode.removeChild(header_node);
													}
												}
                                                _.each(commbo_line_2_delete, function(item){
													var topping_line =  item.get_topping_list(true);
										        	if(topping_line.length){
														for(var i in topping_line){
															var recompute_promotion_id = topping_line[i].promotion_line_id ? topping_line[i].promotion_line_id : topping_line[i].promotion_line_temp_id;
								                            if(recompute_promotion_id){
								                                order.reset_promotion_line_no_render(recompute_promotion_id);
								                            }
														}
													}
                                                    order.remove_orderline(item);
                                                })
												var recompute_promotion_id = selected_orderline.promotion_line_id ? selected_orderline.promotion_line_id : selected_orderline.promotion_line_temp_id;
                                                if(recompute_promotion_id){
                                                    order.reset_promotion_line_no_render(recompute_promotion_id);
                                                }
                                                order.compute_promotion();
												order.rerender_all_line();
//												this.pos.chrome.screens.products.order_widget.renderElement('scroll');
                    //		    				order.checked_promotion = false;
                                            }else{
                                                self.gui.show_popup('error',_t('Sai mật khẩu !'));
                                            }
                                        }
                                    });
                                },
                            });
                        },
                    });
                }else{
                    self.gui.show_popup('selection',{
                        'title': _t('Chọn người có quyền ?'),
                        'list': list_rules,
                        'confirm':function(rule){
                            self.gui.show_popup('passtextinputwidget',{
                                'title': _t('Password ?'),
                                confirm: function(pw) {
                                    if (pw == rule.destroy_order_password){
                                    	order.log_history_permisson('destroy_order_line', rule.id, false, selected_orderline.product.id);
                                        order.remove_orderline(selected_orderline);
                                        //Thai: Xóa các sản phẩm thuộc cùng Combo
                                        var orderlines = order.orderlines.models;
                                        var commbo_line_2_delete = orderlines.filter(function(item){
                                            return item.combo_id == selected_orderline.combo_id && item.is_done_combo == true && item.combo_seq == selected_orderline.combo_seq;
                                        })
										if(commbo_line_2_delete.length){
											var header_node = commbo_line_2_delete[0].node.previousElementSibling;
											if(header_node && !$(header_node).hasClass('orderline')){
												header_node.parentNode.removeChild(header_node);
											}
										}
                                        _.each(commbo_line_2_delete, function(item){
											var topping_line =  item.get_topping_list(true);
								        	if(topping_line.length){
												for(var i in topping_line){
													var recompute_promotion_id = topping_line[i].promotion_line_id ? topping_line[i].promotion_line_id : topping_line[i].promotion_line_temp_id;
						                            if(recompute_promotion_id){
						                                order.reset_promotion_line_no_render(recompute_promotion_id);
						                            }
												}
											}
                                            order.remove_orderline(item);
                                        })
										var recompute_promotion_id = selected_orderline.promotion_line_id ? selected_orderline.promotion_line_id : selected_orderline.promotion_line_temp_id;
                                        if(recompute_promotion_id){
                                            order.reset_promotion_line_no_render(recompute_promotion_id);
                                        }
                                        order.compute_promotion();
										order.rerender_all_line();
//										this.pos.chrome.screens.products.order_widget.renderElement('scroll');
            //		    				order.checked_promotion = false;
                                    }else{
                                        self.gui.show_popup('error',_t('Sai mật khẩu !'));
                                    }
                                }
                            });
                        },
                    });
                }
            }
        },
        set_reward_code: function(){
			return;
            // Thai: Set Mã dự thưởng khi bấm "Thanh toán" ở màn hình sản phẩm
//            var order = this.pos.get_order();
//            var reward_orderline = order.orderlines.models.filter(function(item){
//                return item.product.default_code == 'reward_code';
//            })
//            if ((reward_orderline.length > 0) && (!order.reward_code) && (!order.done_reward_code)){
//                rpc.query({
//                    model:'pos.order',
//                    method: 'get_reward_code',
//                    args: [reward_orderline[0].quantity, reward_orderline[0].promotion_line_id],
//                }).then(function (vals) {
//                    order.reward_code = vals[0];
//                    order.reward_description = vals[1];
//                });
//            }
        },
		block_ui_on_use_combo: function(block) {
			if(block){
				$(".content-order").addClass('overlaypos');
				$(".pos-topheader").addClass('overlaypos');
				$(".header-product .js-category-switch").addClass('overlaypos');
				$(".two-row-second").addClass('overlaypos');
				$(".item-method-promo:not('.choose-combo')").addClass('overlaypos');
			}else{
				$(".content-order").removeClass('overlaypos');
				$(".pos-topheader").removeClass('overlaypos');
				$(".header-product .js-category-switch").removeClass('overlaypos');
				$(".two-row-second").removeClass('overlaypos');
				$(".item-method-promo:not('.choose-combo')").removeClass('overlaypos');
			}
		},
        renderElement: function() {
        	var self = this;
            this._super();
            var button_pay = this.$el.find('.button.pay');
            $(button_pay).click(function(){
                $('.oe_hidden.button.pay').trigger('click');
//                self.set_reward_code();
            })
            //Customer
            var button_customer = $('.button.popup-customer');
            $(button_customer).click(function(){
				if(self.pos.config.is_callcenter_pos){
					self.gui.show_screen('clientlist');
				}else{
					self.clickPopupCustomer();
				}
            })
            //Label Button
            var button_set_note = $('.set-label');
			button_set_note.text('Label');
            $(button_set_note).click(function(){
            	self.clickSetLabel();
            })
            //Choose Extra Topping
            var button_topping = $('.choose-topping');
            $(button_topping).click(function(){
            	self.clickChooseTopping();
            })
            //Quick Cash Payment
            var button_cash_payment = this.$el.find('.set-cash-payment');
            $(button_cash_payment).click(function(){
//                self.set_reward_code();
				if(self.pos.config.is_callcenter_pos){
					return self.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Không sử dụng chức năng này tại POS Call Center',
			        });
				}
                self.clickQuickCashPayment();
            })
            //Manual discount
            var button_manual_discount = this.$el.find('.set-manual-discount');
            $(button_manual_discount).click(function(){
            	self.clickSetManualDiscount();
            })
            //Apply Coupon
            var button_apply_coupon = this.$el.find('.apply-coupon');
            $(button_apply_coupon).click(function(){
            	self.clickApplyCoupon();
            })
            //Change topping, size
            var button_change_topping = this.$el.find('.change-topping');
            $(button_change_topping).click(function(){
            	self.clickChangeTopping();
            })
            // Show combo
            var button_combo = $('.choose-combo');
            $(button_combo).click(function(){
                var order = self.pos.get_order();
				if(order.check_order_payment_on_account('on_account_emp')){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Combo trên đơn hàng áp dụng thanh toán On Account',
	                })
				}
				if(order.check_order_payment_voucher()){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Combo trên đơn hàng áp dụng thanh toán Voucher',
	                })
				}
				
				var partner = order.get_client();
				if(partner && partner.card_code_pricelist_id){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Combo trên đơn hàng có khách hàng sử dụng bảng giá riêng',
	                })
				}
				
                var list_combo = self.pos.db.list_combo ? self.pos.db.list_combo : [];
                if (button_combo.hasClass('open')){
                    //Vuong: don't show default combo for coupon
                    if (list_combo.filter(function(item){
                        return !item.sale_type_ids.length || item.sale_type_ids.indexOf(order.sale_type_id)>=0
                    })){
                        var combo_except_coupon = list_combo.filter(function(line){
                            return !line.use_for_coupon
                        });
                        var default_combo = combo_except_coupon ? combo_except_coupon[0] : false;
                        if (default_combo){
                            self.pos.chrome.screens.products.product_categories_widget.set_combo(default_combo.id);
                        }
                        self.show_combo_list(true);
                        if (default_combo){
                            self.pos.chrome.screens.products.product_categories_widget.set_combo(default_combo.id);
                        }
                    }
                    button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                } else if (button_combo.hasClass('closed')){
                    if (list_combo.filter(function(item){
                        return !item.sale_type_ids.length || item.sale_type_ids.indexOf(order.sale_type_id)>=0
                    })){
                        self.show_combo_list(false);
                    }
                }
            })
            //Loyalty reward
            var button_loyalty_reward = $('.choose-reward-loyalty');
            $(button_loyalty_reward).click(function(){
				var order = self.pos.get_order();
				if(order.partner_insert_type != 'scan'){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Vui lòng quét thẻ khách hàng để có thể đổi quà',
	                })
				}
            	self.clickChooseRewardLoyalty();
            })
            //Chose Promotion
            var button_choose_promotion = $('.choose-promotion');
            $(button_choose_promotion).click(function(){
            	self.clickChoosePromotion();
            })
            //Disable Loyalty
            var button_disable_loyalty = $('.disable-loyalty');
            $(button_disable_loyalty).click(function(){
            	self.clickDisableLoyalty();
            })
            //Open cashbox
            var button_open_cashbox = this.$el.find('.open-cashbox');
            $(button_open_cashbox).click(function(){
				if(self.pos.config.is_callcenter_pos){
					return self.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Không sử dụng chức năng này tại POS Call Center',
			        });
				}
            	self.clickOpenCashbox();
            })
			//Invoice Info
            var button_invoice_info = this.$el.find('.invoice-info');
            $(button_invoice_info).click(function(){
            	self.clickInputInvoiceInfo();
            })
            //Employee Coupon - Normal Coupon
            var button_choose_coupon = $('.choose-coupon');
            $(button_choose_coupon).click(function(){
				var order = self.pos.get_order();
				if(order.check_order_payment_on_account()){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Coupon trên đơn hàng áp dụng thanh toán On Account',
	                })
				}
				if(order.check_order_payment_voucher()){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Coupon trên đơn hàng áp dụng thanh toán Voucher',
	                })
				}
				var partner = order.get_client();
				if(partner && partner.card_code_pricelist_id){
					return self.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không sử dụng Coupon trên đơn hàng có khách hàng sử dụng bảng giá riêng',
	                })
				}
				var list = [{
                    label: 'Coupon',
                    item:  'coupon',
                	},{
                    label: 'Coupon Nhân viên',
                    item:  'employee_coupon',
                }]
                self.gui.show_popup('selection',{
                    'title': 'Chọn loại Coupon áp dụng',
                    'list': list,
                    'confirm': function(type){
						if(type == 'coupon'){
							self.clickApplyCoupon();
						}else{
							if(self.pos.config.is_callcenter_pos){
								return self.gui.show_popup('alert',{
						              'title': 'ERROR',
						              'body':  'Không sử dụng chức năng này tại POS Call Center',
						        });
							}
							self.clickApplyCouponEmployee();
						}
                    },
                });
            })
            // History Orders
            $('.button.history-order').click(function(){
				var order = self.pos.get_order();
				order.history_query_method = 'get_order_by_query';
                self.gui.show_screen('historyOrders');
            });
			var session_id = this.pos.pos_session.id;
			rpc.query({
                model: 'pos.order',
                method: 'check_draft_order',
                args: [session_id],
            }).then(function(vals){
                if(vals){
					$('.button.history-order').addClass('history-highlight')
				}
            })
            // Open Number Input Widget
            var open_numpad_widget = this.$el.find('.open-numpad-widget');
            $(open_numpad_widget).click(function(){
				var order = self.pos.get_order();
				var selected_orderline = order.get_selected_orderline();
				if(selected_orderline && selected_orderline.product.is_cashless){
		    		return self.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Không thể điều chỉnh số lượng thẻ Cashless.',
			        });
		    	}
                self.gui.show_popup('numberinputwidgetnoplus',{
                    'title': 'Nhập giá trị:' ,
                    'confirm': function(value) {
                        if (isNaN(value)){
                            if (typeof value =='string'){
                                value = value.replace(/,/g,'');
                            }
                        }
                        if (isNaN(value)){
                            self.gui.show_popup('error',_t('Vui lòng nhập đúng giá trị'));
                        }else {
							self.state.trigger('set_value',value);
							return;
                        }
                    }
                });
            })

        },
        show_combo_list: function(is_done_combo, combo_coupon_id=false, check_remove_coupon=false){
            var self = this;
            var order = this.pos.get_order();
            var combo = this.pos.chrome.screens.products.product_categories_widget.combo;
            var combo_id = combo ? combo.id : false;
            var line_in_other_combo = order.orderlines.models.filter(function(line){
                return line.is_done_combo == false && line.combo_id});
            
            //raise warning if combo use with coupon
            if(!is_done_combo && order.combo_coupon_id && !check_remove_coupon){
                return self.gui.show_popup('confirm',{
                    'title': _t('Cảnh báo'),
                    'body': _t('Combo chưa hoàn thành, nếu thoát Coupon sẽ bị gỡ khỏi đơn hàng này. Bạn muốn thoát chứ?'),
                    'confirm': function(){
//                    	order.reset_base_price(true);
//        				order.remove_current_discount();
//        				order.unset_promotion_for_coupon();
                    	if(order.combo_coupon_code){
    						order.unset_coupon_code(order.combo_coupon_code);
    					}
                    	order.set_combo_coupon(false);
        				if (line_in_other_combo.length > 0){
        					_.each(line_in_other_combo, function(line){
                                order.remove_orderline(line);
                            })
        				}
        				
                    	self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo);
                        //Edit label nút Combo
                        var button_combo = $('.choose-combo');
                        if (button_combo.hasClass('open')){
                            button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                        } else if (button_combo.hasClass('closed')){
                            button_combo.removeClass('closed').addClass('open').text('Combo');
                        }
                        
                        order.compute_promotion();
                    },
                });
            }
            if (line_in_other_combo.length > 0){
                self.gui.show_popup('confirm',{
                    'title': _t('Cảnh báo'),
                    'body': _t('Bạn còn COMBO chưa hoàn thành.Bạn muốn thoát chứ?'),
                    confirm: function(){
                        if(!self.pos.config.permission_destroy_line){
                            _.each(line_in_other_combo, function(line){
                                order.remove_orderline(line);
                            })
                            if (combo_coupon_id){
                                self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo, combo_coupon_id, 'render_from_combo_button');
                            } else{
                                self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo, false, 'render_from_combo_button');
                            }
                            
                            //Edit label nút Combo
                            var button_combo = $('.choose-combo');
                            if (button_combo.hasClass('open')){
                                button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                            } else if (button_combo.hasClass('closed')){
                                button_combo.removeClass('closed').addClass('open').text('Combo');
                            }
                        } else{
                            var list_rules = [];
                            _.each(self.pos.rules, function(rule){
                                list_rules.push({
                                    label : rule.name,
                                    item: rule,
                                });
                            });
                            self.pos.chrome.gui.show_popup('selection',{
                                'title': _t('Chọn người có quyền ?'),
                                'list': list_rules,
                                'confirm':function(rule){
                                    self.pos.chrome.gui.show_popup('passtextinputwidget',{
                                        'title': _t('Password ?'),
                                        confirm: function(pw) {
                                            if (pw == rule.destroy_order_password){
                                                _.each(line_in_other_combo, function(line){
                                                    order.remove_orderline(line);
                                                })
                                                if (combo_coupon_id){
                                                    self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo, combo_coupon_id, 'render_from_combo_button');
                                                } else{
                                                    self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo, false, 'render_from_combo_button');
                                                }
                                                //Edit label nút Combo
                                                var button_combo = $('.choose-combo');
                                                if (button_combo.hasClass('open')){
                                                    button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                                                } else if (button_combo.hasClass('closed')){
                                                    button_combo.removeClass('closed').addClass('open').text('Combo');
                                                }
                                            }else{
                                                self.gui.show_popup('error',_t('Sai mật khẩu !'));
                                            }
                                        }
                                    });
                                },
                            });
                        }
                        
                        
                    },
                });
            } else{
                var button_combo = $('.choose-combo');
                if (button_combo.hasClass('open')){
                    button_combo.removeClass('open').addClass('closed').text('Thoát Combo');
                } else if (button_combo.hasClass('closed')){
                    button_combo.removeClass('closed').addClass('open').text('Combo');
                }
                self.pos.chrome.screens.products.product_categories_widget.renderElement(is_done_combo, combo_coupon_id, 'render_from_combo_button');
            }
            
        },
        clickPopupCustomer: function() {
        	var self = this;
        	var order = this.pos.get_order();
        	if(order.check_employee_coupon_using()){
        		return this.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Đơn hàng đang áp dụng Coupon Nhân viên nên không thể chọn khách hàng',
                })
        	}
        	this.gui.show_popup('clientmethod');
        },
        clickSetManualDiscount: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var selected_orderline = order.get_selected_orderline();
        	if(!selected_orderline){
        		return self.gui.show_popup('error',_t('Vui lòng chọn sản phẩm !'));
        	}
        	self.discount_orderline();
//        	order.set_check_scan_manual_discount(true);
//        	self.gui.show_popup('cardscanner',{
//    	    	title: 'Xin hãy quẹt thẻ Quản lý cửa hàng vào máy quét'
//    	    });
        },
        clickOpenCashbox: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	order.set_check_scan_open_cashbox(true);
        	self.gui.show_popup('cardscanner',{
    	    	title: 'Xin hãy quẹt thẻ Quản lý cửa hàng vào máy quét'
    	    });
        },
		clickInputInvoiceInfo: function(){
			var self = this;
			var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
			if(!orderlines.length){
				return this.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Vui lòng chọn sản phẩm trước',
                })
			}
			self.gui.show_popup('invoiceinfoinput');
		},
        set_label_order: function(input_type='set_label_button',error=false, value=false) {
        	var self = this;
        	var order = self.pos.get_order();
        	if(!value){
        		value = order.get_note_label();
        	}
        	this.gui.show_popup('textinput',{
    	    	title: 'Ghi chú trên Label',
    	    	value: value,
    	    	error: error,
    	    	confirm: function(note) {
					if(!note){
						var error = 'Bạn chưa nhập label sản phẩm';
						self.set_label_order(input_type, error, false);
					}else if(note.length <= 20){
    	    			order.set_note_label(note);
						if(input_type=='click_payment'){
							self.gui.show_screen('payment');
						}else if(input_type=='quick_cash_payment'){
							self.clickQuickCashPayment();
						}if(input_type=='show_payment'){
							self.pos.chrome.screens.payment.show();
						}
    	    		}else{
    	    			var error = 'Ghi chú trên label tối đa 20 ký tự';
    	    			self.set_label_order(input_type, error, note);
    	    		}
    	    	},
    	    });
        },
		set_note_call_center: function(error=false) {
        	var self = this;
        	var order = self.pos.get_order();
			self.gui.show_popup('text2area',{
                title: 'Ghi chú',
				error: error,
                confirm: function(note, mobile) {
					order.note_address = note;
					order.note_mobile = mobile;
                	if(mobile && note){
                		note = mobile + ' - ' + note;
                	}
                	if(!note){
                		note = mobile;
                	}
					if(!note){
						var error = 'Vui lòng nhập ghi chú';
						self.set_note_call_center(error);
					}else{
						order.set_note(note);
						self.gui.show_screen('payment');
					}
                },
            });
        },
		clickSetLabel: function() {
        	var self = this;
        	self.set_label_order();
        },
        clickChooseTopping: function() {
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines();
        	if(!orderlines.length){
        		return this.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Vui lòng chọn món trước.',
                })
        	}else{
        		var selected_orderline = order.get_selected_orderline();
        		this.gui.show_popup('extra_topping',{
            		'orderline': selected_orderline,
        	    });
        	}
        },
        clickChangeTopping: function() {
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.get_orderlines();
        	if(!orderlines.length){
        		return this.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Vui lòng chọn món trước.',
                })
        	}else{
        		var selected_orderline = order.get_selected_orderline();
        		return this.gui.show_popup('topping_poppup',{
                    'product': selected_orderline.product,
                    'orderline': selected_orderline,
                    'default_qty': selected_orderline.get_quantity(),
                    'default_topping_list': selected_orderline.get_topping_list(),
                    'cup_type_default': selected_orderline.cup_type_default,
					'is_done_combo': selected_orderline.is_done_combo,
                });
        	}
        },
        clickQuickCashPayment: function() {
        	var self = this;
        	var order = this.pos.get_order();
			if(order.check_all_order_with_other_promo()){
				self.gui.show_screen('products');
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'CTKM giảm giá trên toàn đơn không áp dụng với CTKM khác, vui lòng kiểm tra lại.',
                });
			}
			if(order.check_promotion_discount_limit()){
				self.gui.show_screen('products');
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Sản phẩm giảm giá vượt quá số lượng cho phép, vui lòng kiểm tra lại.',
                });
			}
        	if(!order.get_note_label()){
				this.set_label_order('quick_cash_payment');
				return;
        	}
            $('.oe_hidden.button.pay').trigger('click');
            var amount_total = order.get_total_with_tax();
            var amount = amount_total - order.get_total_paid();
            if(amount_total > 0 && amount > 0){
            	order.add_paymentline( self.pos.payment_methods[0]);
                order.selected_paymentline.set_amount(amount);
//                order.selected_paymentline.set_currency(order.selected_paymentline.pos.company_currency, amount, 1);
            	self.pos.chrome.screens.payment.reset_input();
                self.pos.chrome.screens.payment.render_paymentlines();
            }
        },
        open_coupon_popup: function(){
        	var self = this;
            var order  = this.pos.get_order();
            var orderlines = order.orderlines;
            if(order.check_origin_order() && !order.check_order_with_loyalty_discount()){
            	order.reset_base_price(true);
				order.remove_current_discount();
            	return this.gui.show_popup('textinput',{
                    title: _t('Nhập mã Coupon'),
                    off_focus: true,
        	    	confirm: function(code) {
        	    		var coupon_code = ({code:code});
        	    		var search_type = 'coupon';
        	    		order.get_coupon_by_code_w_combo(coupon_code,search_type);
        	    	},
        	    	cancel: function() {
        	    		order.compute_promotion_after_reset_price();
        	    	},
        	    });
            }else{
            	return self.gui.show_popup('confirm',{
        			'title':  _t('Sử dụng Coupon trên đơn hàng nguyên giá'),
                    'body':  _t('Nếu xác nhận sử dụng Coupon trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                    'confirm': function() {
                    	order.reset_base_price(true);
        				order.remove_current_discount();
						order.unset_promotion_for_coupon();
						order.set_disable_loyalty_discount(true);
                    	order.remove_loyalty_discount();
						order.remove_combo_done();
                    	this.gui.show_popup('textinput',{
                            title: _t('Nhập mã Coupon'),
                            off_focus: true,
                	    	confirm: function(code) {
                	    		var coupon_code = ({code:code});
                	    		var search_type = 'coupon';
                	    		order.get_coupon_by_code_w_combo(coupon_code,search_type);
                	    	},
                	    	cancel: function() {
                	    		order.compute_promotion_after_reset_price();
                	    	},
                	    });
                    },'cancel': function() {
                    	order.compute_promotion_after_reset_price();
                    },
                });
            }
        },
        clickApplyCoupon: function() {
        	var self = this;
            var order  = this.pos.get_order();
            var orderlines = order.orderlines;
            if(order.combo_coupon_id){
            	return this.pos.chrome.gui.show_popup('alert',{
	  	              'title': 'Cảnh báo',
	  	              'body':  'Vui lòng hoàn thành Combo trước !!!',
            	});
            }
            if(order.coupon_code_array.length && !order.coupon_code_array.includes(order.current_coupon_code)){
            	self.gui.show_popup('couponmethod');
            }else{
            	self.open_coupon_popup();
            }
            
        },
        clickApplyCouponEmployee: function(){
        	var self = this;
            var order  = this.pos.get_order();
            var orderlines = order.get_orderlines();
            if(!orderlines.length){
            	return this.pos.chrome.gui.show_popup('alert',{
    	              'title': 'ERROR',
    	              'body':  'Vui lòng chọn sản phẩm trước !!!',
    	        });
            }
            if(order.check_origin_order() && !order.check_order_with_loyalty_discount()){
            	order.reset_base_price(true);
				order.remove_current_discount();
				order.set_check_scan_employee_coupon(true);
				return self.gui.show_popup('cardscanner',{
	    	    	title: 'Xin hãy quẹt thẻ nhân viên vào máy quét',
	    	    	cancel: function() {
	                	order.compute_promotion_after_reset_price();
	                },
	    	    }); 
            }else{
            	return self.gui.show_popup('confirm',{
        			'title':  _t('Sử dụng Coupon Nhân viên trên đơn hàng nguyên giá'),
                    'body':  _t('Nếu xác nhận sử dụng Coupon trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                    'confirm': function() {
                    	order.reset_base_price(true);
        				order.remove_current_discount();
						order.unset_promotion_for_coupon();
        				order.set_check_scan_employee_coupon(true);
						order.set_disable_loyalty_discount(true);
                    	order.remove_loyalty_discount();
						order.remove_combo_done();
        				self.gui.show_popup('cardscanner',{
        	    	    	title: 'Xin hãy quẹt thẻ nhân viên vào máy quét',
        	    	    	cancel: function() {
        	                	order.compute_promotion_after_reset_price();
        	                },
        	    	    });
                    }
                });
            }
        	
        },
        clickChooseRewardLoyalty: function(){
        	var order  = this.pos.get_order();
            var client = order.get_client(); 
            if (!client) {
            	return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Vui lòng nhập khách hàng trước',
                });
            }

            var rewards = order.get_available_rewards();
            if (rewards.length === 0) {
                this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Không có quà tặng khả dụng',
                });
                return;
            }else { 
				if(!order.check_condition_loyalty_order()){
					return this.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Không thể chọn quà tặng loyalty trên đơn hàng áp dụng khuyến mãi toàn đơn',
	                });
				}
                var list = [];
                for (var i = 0; i < rewards.length; i++) {
                	var reward_name = rewards[i].name;
                	reward_name = reward_name + ' -' + rewards[i].point_cost + ' điểm'
                	if(rewards[i].length > 1 && rewards[i][0]=='birthday'){
                		reward_name = 'Quà tặng sinh nhật'
                	}
                    list.push({
                        label: reward_name,
                        item:  rewards[i],
                    });
                }
                this.gui.show_popup('selection',{
                    'title': 'Vui lòng chọn quà tặng',
                    'list': list,
                    'confirm': function(reward){
                        order.apply_reward(reward);
                    },
                });
            }
        },
        clickChoosePromotion: function(){
        	var self = this;
        	var order = this.pos.get_order();
			if(order.check_order_payment_on_account()){
				return self.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Không sử dụng khuyến mãi trên đơn hàng áp dụng thanh toán On Account',
                })
			}
			if(order.check_order_payment_voucher()){
				return self.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Không sử dụng khuyến mãi trên đơn hàng áp dụng thanh toán Voucher',
                })
			}
			
			var partner = order.get_client();
			if(partner && partner.card_code_pricelist_id){
				return self.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Không sử dụng khuyến mãi trên đơn hàng có khách hàng sử dụng bảng giá riêng',
                })
			}
			
        	var orderlines = order.get_orderlines();
        	var orderline_to_promo = orderlines.filter(function(line) 
//				{return !line.is_topping_line && !line.combo_id && !line.is_promotion_line && !line.is_birthday_promotion;}
				{return !line.combo_id && !line.is_promotion_line && !line.is_birthday_promotion && !line.reward_id}
    		);
    		if(!orderline_to_promo.length){
    			return this.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Không có sản phẩm thỏa mãn chương trình khuyến mãi',
                });
    		}else{
    			var all_promotion = order.get_promotion_no_condition(false, orderline_to_promo);
				var promotion_all_order = [];
				_.each(all_promotion, function(promo){
					if(['order', 'combo', 'list_cat'].includes(promo.product_attribute)){
						promotion_all_order.push(promo);
					}
				})
    			var loyalty_line = orderlines.filter(function(line) 
    				{return line.canbe_loyalty_line}
        		);
    			if(loyalty_line.length){
    				all_promotion.push({'id':'loyalty', 'display_name':'Chiết khấu Loyalty'})
    			}
				//promotion coupon product
				var product_coupon_line = orderlines.filter(function(line) 
    				{return line.product_coupon_code && line.cup_type == 'themos' && line.promotion_line_id}
        		);
				var product_coupon_line_list = [];
				_.each(product_coupon_line, function(line){
					if(!product_coupon_line_list.includes(line.promotion_line_id)){
						product_coupon_line_list.push(line.promotion_line_id);
						var promo_line = self.pos.promotion_lines[line.promotion_line_id][0];
						all_promotion.push(promo_line)
					}
				})
				
    			if(all_promotion.length){
    				this.gui.show_popup('select_promotion_widget',{
                        'title': 'Chương trình khuyến mãi',
                        'orderlines': orderline_to_promo,
                        'promotion_ids':all_promotion,
						'promotion_all_ids':promotion_all_order,
                    });
    			}else{
    				return this.gui.show_popup('alert',{
                        'title': 'ERROR',
                        'body':  'Không có sản phẩm thỏa mãn chương trình khuyến mãi',
                    });
    			}
    			
    		}
        },
        clickDisableLoyalty: function(){
        	var self = this;
        	var order = this.pos.get_order();
        	var orderlines = order.orderlines;
        	var client = order.get_client();
        	if(client){
        		if(!order.disable_loyalty_discount){
        			return self.gui.show_popup('confirm',{
            			'title':  'Khóa Loyalty',
                        'body':  'Các sản phẩm nguyên giá sẽ không được hưởng chiết khấu Loyalty. Nếu đồng ý hãy nhấn Xác nhận',
                        'confirm': function() {
                        	order.set_disable_loyalty_discount(true);
                        	order.remove_loyalty_discount();
                        },
                    });
        		}else{
        			order.set_disable_loyalty_discount(false);
        			order.checked_loyalty_level = false;
                    order.set_unchecked_disc_loyalty();
            		order.set_unchecked_disc_birthdate();
        		}
        	}
        }
    });
    screens.OrderWidget.include({
        set_value: function(val) {
            // this._super(val);
			var self = this;
            var order = this.pos.get_order();
            var selected_line = order.get_selected_orderline();
            if (selected_line) {
				if(selected_line.product.is_cashless){
		    		return self.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Không thể điều chỉnh số lượng thẻ Cashless.',
			        });
		    	}
				if(selected_line.combo_id && !selected_line.is_done_combo){
		    		return self.gui.show_popup('alert',{
			              'title': 'Cảnh báo',
			              'body':  'Vui lòng hoàn tất Combo trước khi điều chỉnh số lượng.',
			        });
		    	}
                if(selected_line.combo_id && selected_line.is_done_combo){
					var current_quantity = parseInt(selected_line.quantity);
                    var combo_seq = selected_line.combo_seq || 0;
                    if (combo_seq != 0){
						var combo_first_qty_input = selected_line.first_qty_input || 1;
						var combo_rate_check = val/combo_first_qty_input;
						var combo_rate = val/current_quantity;
						if(!Number.isInteger(combo_rate_check)){
							return self.pos.gui.show_popup('alert',{
                                'title': 'Cảnh báo',
                                'body':  'Vui lòng nhập só lượng là bội số của sản phẩm trong combo!',
                            });
						}
                        var order_line_w_same_commbo = order.orderlines.models.filter(function(item){
                            return item.combo_id == selected_line.combo_id && item.combo_seq == combo_seq;
                        })
						selected_line.combo_qty = combo_rate;
                        _.each(order_line_w_same_commbo, function(item){
							item.combo_qty = combo_rate;
                            item.set_quantity(parseInt(item.quantity*combo_rate), true);
                        })

						var total_combo_amount = 0;
	                    var total_combo_qty = 0;
						var combo = self.pos.db.list_combo.filter(function(cb){
	                        return cb.id == selected_line.combo_id;
	                    })
						_.each(order_line_w_same_commbo, function(line){
	                        total_combo_amount += (line.get_quantity_str()*line.get_unit_display_price());
	                        var _topping_lines = order.orderlines.models.filter(function(topping){
	                            return topping.related_line_id == line.fe_uid;
	                        })
	                        _.each(_topping_lines, function(l){
	                            total_combo_amount += (l.get_quantity_str()*l.get_unit_display_price());
	                        })
	                        total_combo_qty = parseInt(line.quantity/line.combo_qty);
	                    })
	                    var combo_title_html = QWeb.render('ComboTitle',{widget:self, combo:combo[0], total_combo_amount:total_combo_amount, total_combo_qty:total_combo_qty});
						_.each(order_line_w_same_commbo, function(line){
							//change combo header
							if(line.node){
								var header_node = line.node.previousElementSibling;
								if(header_node && !$(header_node).hasClass('orderline')){
									var elnode = document.createElement('div');
			                        elnode.innerHTML = _.str.trim(combo_title_html);
			                        elnode = elnode.childNodes[0];
									header_node.replaceWith(elnode);
								}
							}
		                })
//						self.pos.chrome.screens.products.order_widget.renderElement();
                    }
                }
                else{
                    this._super(val);
                }
				self.pos.chrome.screens.products.order_widget.renderElement();
            }
        },
    	orderline_change: function(line){
    		if(!line.is_topping_line && line.product.default_code != 'reward_code'){
	            this.rerender_orderline(line);
	            this.update_summary();
            }
//            this.renderElement();
        },
        
        orderline_remove: function(line){
        	if(line.is_topping_line || line.product.default_code == 'reward_code'){
        		return
        	}
            this.remove_orderline(line);
            this.numpad_state.reset();
            this.update_summary();
//            this.renderElement();
        },
    	renderElement: function(scrollbottom){
            var self = this;
            var order  = this.pos.get_order();
            if (!order) {
                return;
            }
            var orderlines = order.get_orderlines();
            
            var el_str  = QWeb.render('OrderWidget',{widget:this, order:order, orderlines:orderlines});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];
            var list_container = el_node.querySelector('.orderlines');
            var line_rendered = [];
            for(var i = 0, len = orderlines.length; i < len; i++){
                var orderline = orderlines[i];
                if(orderline.product.default_code == 'reward_code'){
                    continue
                }
                if (line_rendered.indexOf(orderline.id) >0){
                    continue
                }
                if (orderline.is_done_combo == false){
                    if(!orderline.is_topping_line){
                        var orderline = this.render_orderline(orderline);
                        list_container.appendChild(orderline);
                    }
                    line_rendered.push(orderline.id);
                } else{
                    var combo = this.pos.db.list_combo.filter(function(combo){
                        return combo.id == orderline.combo_id;
                    })
                    var commbo_seq = orderline.combo_seq;
					var total_combo_amount = 0;
                    var order_line_in_combo = orderlines.filter(function(item){
                        return item.combo_id == combo[0].id && item.is_done_combo == true && item.combo_seq == commbo_seq;
                    })
                    var total_combo_qty = 0;
					_.each(order_line_in_combo, function(line){
                        total_combo_amount += (line.get_quantity_str()*line.get_unit_display_price());
                        var _topping_lines = orderlines.filter(function(topping){
                            return topping.related_line_id == line.fe_uid;
                        })
                        _.each(_topping_lines, function(l){
                            total_combo_amount += (l.get_quantity_str()*l.get_unit_display_price());
                        })
                        total_combo_qty = parseInt(line.quantity/line.combo_qty);
                    })
                    var combo_title_html = QWeb.render('ComboTitle',{widget:self, combo:combo[0], total_combo_amount:total_combo_amount, total_combo_qty:total_combo_qty});
                    var elnode = document.createElement('div');
                        elnode.innerHTML = _.str.trim(combo_title_html);
                        elnode = elnode.childNodes[0];
                    list_container.appendChild(elnode);
                    _.each(order_line_in_combo, function(item){
                        if(!item.is_topping_line){
                            var line = self.render_orderline(item);
                            list_container.appendChild(line);
                        }
                        line_rendered.push(item.id)
                    })
                }
                
            }
            
            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            this.update_summary();
            
            // Thái: Mặc định scroll to bottom
	        if(scrollbottom){
	            this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
	        }
//            this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
			$(this.el).find('.type-name').click(function () {
				if(self.pos.config.is_callcenter_pos){
					order.change_warehouse_call_center();
				}else{
					self.change_sale_type();
				}
            })

			var product_categories_widget = this.pos.chrome.screens.products.product_categories_widget;
			if(product_categories_widget && product_categories_widget.combo){
				$(".content-order").addClass('overlaypos');
			}
        },

		change_sale_type: function(){
			var self = this;
			var list = [];
            _.each(globalThis.posmodel.db.sale_type_ids, function(sale_type){
                list.push({
                    label : sale_type.name,
                    item: sale_type,
                });
            });
            return self.gui.show_popup('saletype',{
                'list': list,
                'confirm':function(item){
                    var order = this.posmodel.get_order();
                    var line_in_other_combo = order.orderlines.models.filter(function(line){
                        return (line.is_done_combo == false && line.combo_id) || line.is_done_combo});
                    var combo_for_this_sale_type = self.pos.db.list_combo.filter(function(combo){
                        return !combo.sale_type_ids.length || combo.sale_type_ids.indexOf(item.id) >=0;
                    })
                    var sale_type_combo_ids = [];
                    _.each(combo_for_this_sale_type, function(combo){
                        sale_type_combo_ids.push(combo.id)
                    })
                    var line_to_delete = line_in_other_combo.filter(function(line){
                        return sale_type_combo_ids.indexOf(line.combo_id) < 0
                    });
                    var combo_name_to_delete = []
                    _.each(line_to_delete, function(line){
                        var combo = self.pos.db.get_combo_by_id(line.combo_id);
                        if (combo_name_to_delete.indexOf(combo.name) < 0){
                            combo_name_to_delete.push(combo.name)
                        }
                    })
                    var combo_list_name = combo_name_to_delete.join(', ');
                    if (line_to_delete.length >0){
                        self.gui.show_popup('confirm',{
                            'title': _t('Cảnh báo'),
                            'body': _t('COMBO: ' + combo_list_name + ' không khả dụng cho ' + item.name + '. Xác nhận để xóa COMBO này khỏi đơn hàng.'),
                            confirm: function(){
                                if(!self.pos.config.permission_destroy_line){
                                    _.each(line_to_delete, function(line){
										if(line.node){
											var header_node = line.node.previousElementSibling;
											if(header_node && !$(header_node).hasClass('orderline')){
												header_node.parentNode.removeChild(header_node);
											}
										}
                                        order.remove_orderline(line);
                                        order.set_sale_type(item);
                                        self.pos.chrome.screens.products.product_categories_widget.renderElement(false);
                                    })
                                    //Edit label nút Combo
                                    var button_combo = $('.choose-combo');
                                    if (button_combo.hasClass('closed')){
                                        button_combo.removeClass('closed').addClass('open').text('Combo');
                                    }
                                } else{
                                    var list_rules = [];
                                    _.each(self.pos.rules, function(rule){
                                        list_rules.push({
                                            label : rule.name,
                                            item: rule,
                                        });
                                    });
                                    self.pos.chrome.gui.show_popup('selection',{
                                        'title': _t('Chọn người có quyền ?'),
                                        'list': list_rules,
                                        'confirm':function(rule){
                                            self.pos.chrome.gui.show_popup('passtextinputwidget',{
                                                'title': _t('Password ?'),
                                                confirm: function(pw) {
                                                    if (pw == rule.destroy_order_password){
														if(line_to_delete.length){
															var header_node = line_to_delete[0].node.previousElementSibling;
															if(header_node && !$(header_node).hasClass('orderline')){
																header_node.parentNode.removeChild(header_node);
															}
														}
                                                        _.each(line_to_delete, function(line){
															if(line.node){
																var header_node = line.node.previousElementSibling;
																if(header_node && !$(header_node).hasClass('orderline')){
																	header_node.parentNode.removeChild(header_node);
																}
															}
                                                            order.remove_orderline(line);
                                                            order.set_sale_type(item);
                                                            self.pos.chrome.screens.products.product_categories_widget.renderElement(false);
                                                        })
                                                        //Edit label nút Combo
                                                        var button_combo = $('.choose-combo');
                                                        if (button_combo.hasClass('closed')){
                                                            button_combo.removeClass('closed').addClass('open').text('Combo');
                                                        }
                                                    }else{
                                                        self.gui.show_popup('error',_t('Sai mật khẩu !'));
                                                    }
                                                }
                                            });
                                        },
                                    });
                                }
                            },
                        });
                    } else{
                        order.set_sale_type(item);
                        self.pos.chrome.screens.products.product_categories_widget.renderElement(false);
                    }
                }
            });
		},

        update_summary: function(){
        	var order = this.pos.get_order();
        	var coupon_code = order ? order.coupon_code_list : false;
        	var coupon_code_array = order ? order.coupon_code_array : [];
        	var coupon_qty = coupon_code_array.length;
    		this.el.querySelector('.coupon-qty.value').textContent = coupon_qty;
        	
        	if(this.getParent().actionpad && this.getParent().actionpad.$el.find('.disable-loyalty')){
        		var disable_loyalty = order ? order.disable_loyalty_discount : false;
        		if(disable_loyalty){
        			this.getParent().actionpad.$el.find('.disable-loyalty').text('Mở Loyalty');
        		}else{
        			this.getParent().actionpad.$el.find('.disable-loyalty').text('Khoá Loyalty');
        		}
        	}
        	if (this.pos.get_loyalty_program() && this.getParent().actionpad && this.getParent().actionpad.$el.find('.choose-reward-loyalty')) {
                var rewards = order.get_available_rewards();
                if(rewards.length && order.partner_insert_type == 'scan'){
                	this.getParent().actionpad.$el.find('.choose-reward-loyalty').addClass('highlight');
                }else{
                	this.getParent().actionpad.$el.find('.choose-reward-loyalty').removeClass('highlight');
                }
            }
			if (this.getParent().actionpad && this.getParent().actionpad.$el.find('.button.history-order')) {
                var draft_order_count = this.pos.draft_order_count || 0;
                if(draft_order_count){
                	this.getParent().actionpad.$el.find('.button.history-order').addClass('history-highlight');
                }else{
                	this.getParent().actionpad.$el.find('.button.history-order').removeClass('history-highlight');
                }
            }
			if (this.getParent().numpad && this.getParent().numpad.$el.find('.button.invoice-info')) {
                if(order.invoice_request){
                	this.getParent().numpad.$el.find('.invoice-info').addClass('highlight');
                }else{
                	this.getParent().numpad.$el.find('.invoice-info').removeClass('highlight');
                }
            }
        	var $loypoints = $(this.el).find('.wrap-detail-customer.summary');
        	var partner = order ? order.get_client() : false;
            var partner_level = partner ? partner.loyalty_level_id : false;
            var level_name = partner ? order.get_loyalty_level_name_by_id(partner_level[0]) : '';
            var points_old      = (partner && !partner.card_code_pricelist_id && !partner.use_for_on_account) ? partner.total_point_act : 0;
            var points_won      = partner ? order.get_won_points() : 0;
            var points_spent    = partner ? order.get_spent_points() : 0;
            var points_total    = partner ? order.get_new_points() : 0;
            if(check_loyalty == true){
                partner = order ? order.get_client() : false;
                partner_level = partner ? partner.loyalty_level_id : false;
                level_name = order.get_loyalty_level_name_by_id(partner_level[0]);
                points_old      = this.pos.get_client().total_point_act;
                points_won      = order.get_won_points();
                points_spent    = order.get_spent_points();
                points_total    = order.get_new_points();
            }
            $loypoints.empty();
            $loypoints.html($(QWeb.render('LoyaltyPoints',{ 
                widget: this, 
                partner: partner,
                partner_level: partner_level,
                level_name: level_name,
                rounding: this.pos.get_loyalty_program().rounding,
                points_old: points_old,
                points_won: points_won,
                points_spent: points_spent,
                points_total: points_total,
            })));
            
            this._super();
            
            var order_sale_type_name = this.pos.get_order().sale_type_name;
            var $order_type = $(this.el).find('.content-order .type-name');
            var logo = this.pos.db.sale_type_ids[this.pos.get_order().sale_type_id].logo;
            $(this.el).find('.orderlines img').attr('src','data:image/png;base64,'+logo);
            $($order_type).text(order_sale_type_name);
            if (!order.get_orderlines().length) {
                 return;
            }
            var loyalty = this.pos.get_loyalty_program();
            var check_loyalty = false;
            
            if(loyalty && order.get_client() && order.get_client().mobile !== '0000000000'){
                if(loyalty.partner_category_ids.length){
                    for(var i in loyalty.partner_category_ids){
                        for(var j in order.get_client().category_id)
                        if(loyalty.partner_category_ids[i] == order.get_client().category_id[j]){
                            check_loyalty = true;
                        }
                    }
                }else{
                    check_loyalty = true;
                }
            }
            if (this.pos.get_loyalty_program() &&
                this.getParent().action_buttons &&
                this.getParent().action_buttons.loyalty) {
                var rewards = order.get_available_rewards();
                this.getParent().action_buttons.loyalty.highlight(!!rewards.length);
            }
            
            var order_line = this.pos.get_order().get_orderlines_no_topping()
            var total_label = 0;
            _.each(order_line, function(line){
                if(line.product.default_code != 'reward_code'){
                    total_label+=line.quantity;
                }
            });
            this.el.querySelector('.summary .total > .quantity.value').textContent = parseInt(total_label);
            $(this.el).find('.wrap-detail-bill.summary .customer_info').remove();
            order.compute_surcharge_order();
            var surcharge = order.total_surcharge;
            this.el.querySelector('.summary .total > .surcharge.value').textContent = this.format_currency_no_symbol(surcharge);
            var total     = order ? order.get_total_with_tax() : 0;
            var discount_amount = order ? order.discount_amount : 0;
            var discount_lines = order ? order.get_total_discount() : 0;
            var subtotal = total - discount_amount + discount_lines - surcharge
            var total_discount = discount_amount - discount_lines;
            if(order && order.sale_type_id){
            	var sale_type = this.pos.db.sale_type_ids[order.sale_type_id];
                if(sale_type && sale_type.show_original_subtotal){
                	subtotal = order.get_total_list_price();
                	total_discount = total - subtotal;
                }
            }
            this.el.querySelector('.summary .total > .subtotal.value').textContent = this.format_currency_no_symbol(subtotal);
            this.el.querySelector('.summary .total > .discount.value').textContent = this.format_currency_no_symbol(total_discount);
            this.el.querySelector('.summary .total > .total_amount.value').textContent = this.format_currency_no_symbol(total);
        }
    });
    screens.ReceiptScreenWidget.include({
        print: function() {
            var count = parseInt(this.$('#number_count').html()) +1;
            if (count > 1){
                this.$('#number_count').closest('.printed').css('display', 'block');
                this.$('#receipt').css('display', 'none');
            }
            var order = this.pos.get_order();
            var self = this;
            self.$('#number_count').html(count);
            self.$('#lasted-print').css('display', 'block').html(moment().format('L LT'));
            rpc.query({
                model:'pos.order',
                method: 'set_count_of_print_bill',
                args: [order.name],
            })
            if (self.pos.config.use_multi_printer){
                var bills = $('.pos-receipt-container-bill .pos-sale-ticket');
                _.each(bills, function(bill){
                    var printer_name = $(bill).attr('label');
					var bill_type = $(bill).attr('name');
                    if (printer_name == 'POS Order' && bill_type != 'kitchen-bill'){
                        qz.printers.find(printer_name).then(function(printer) {
                            var config = qz.configs.create(printer);
                            var data = [{
                                type: 'pixel',
								format: 'html',
								flavor: 'plain',
                                data: $(bill).html()
                            }];  // Raw ZPL
                            qz.print(config, data);
                        }).catch(function(e) {
                            self.pos.gui.show_popup('alert',{
                                'title': 'ERROR',
                                'body':  'Không tìm thấy máy in bill',
                            });
                        });
                    }
                })
            } else{
                self._super();
            }
            
        },
    });
    screens.PaymentScreenWidget.include({
		click_back: function(){
			var order = this.pos.get_order();
			var lines = order.get_paymentlines();
			if(order.check_order_payment_voucher()){
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Vui lòng xóa thanh toán Voucher nếu muốn điều chỉnh đơn hàng',
                });
			}
			if(order.check_order_payment_on_account()){
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Vui lòng xóa thanh toán On Account nếu muốn điều chỉnh đơn hàng',
                });
			}
	        for ( var i = 0; i < lines.length; i++ ) {
	        	if(lines[i].payment_method.use_for=='visa'){
					return this.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Vui lòng xóa thanh toán Visa nếu muốn điều chỉnh đơn hàng',
	                });
	        	}
	        }
			if(lines.length){
				order.remove_all_order_payment();
			}
			this._super();
	    },
		get_loyalty: function(){
			var self = this;
			var order = this.pos.get_order();
			if(order.check_all_order_with_other_promo()){
				self.gui.show_screen('products');
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'CTKM giảm giá trên toàn đơn không áp dụng với CTKM hoặc chiết khấu Loyalty khác, vui lòng kiểm tra lại.',
                });
			}
			if(order.check_promotion_discount_limit()){
				self.gui.show_screen('products');
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Sản phẩm giảm giá vượt quá số lượng cho phép, vui lòng kiểm tra lại.',
                });
			}
			if(order.check_promotion_reward()){
				self.gui.show_screen('products');
				return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Vui lòng chỉ áp dụng 1 chương trình Mã dự thưởng trên đơn hàng.',
                });
			}
			if(order.promotion_for_coupon.length){
				var orderlines = order.get_orderlines();
				var check_promotion_coupon = true;
				_.each(order.promotion_for_coupon, function(promo_line){
					var line_promo = orderlines.filter(function(l){
						return l.promotion_line_id == promo_line.id
					})
					if(!line_promo.length){
						check_promotion_coupon = false;
					}
				})
				if(!check_promotion_coupon){
					self.gui.show_screen('products');
					return this.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Đơn hàng có áp dụng coupon nhưng không có khuyến mãi tương ứng. Vui lòng chọn lại khuyến mãi hoặc sử dụng chức năng Hủy coupon',
	                });
				}
				
			}
			if(order.order_in_app || order.linked_draft_order_be){
				return;
			}
			this._super();
			var numpad = self.chrome.screens.products.numpad;
			if(self.gui.current_screen != self){
					return;
			}else{
				if(!order.get_note_label() && !self.pos.config.is_callcenter_pos){
					self.gui.show_screen('products');
	        		numpad.set_label_order('click_payment');
					return;
	        	}
				if(self.pos.config.is_callcenter_pos){
					if(!order.note){
						self.gui.show_screen('products');
		        		numpad.set_note_call_center();
						return;
					}
					if(!order.warehouse_callcenter_id){
						self.gui.show_screen('products');
		        		order.change_warehouse_call_center('show_payment_screen');
						return;
					}
				}
			}
		},
        show: function(){
            this.renderElement();
            var order = this.render_order();
            this.$('.placeholder-Order').empty();
            order.appendTo(this.$('.placeholder-Order'));
            this._super();
            
            var orderlines = this.pos.get_order().orderlines;
    		for (var i=0; i < orderlines.length; i++){
    			if(orderlines.models[i].is_loyalty_line && !orderlines.models[i].is_topping_line){
    				orderlines.models[i].trigger('change', orderlines.models[i]);
    			}
            }
        },
		bill_print_qz: function(check_payment_cash){
			var self = this;
			var lines = self.pos.get_order().get_paymentlines();
			var bills = $('.pos-receipt-container-bill .pos-sale-ticket');
			var chain = [];
			var error = [];
            _.each(bills, function(bill, i){
                var printer_name = $(bill).attr('label');
				var bill_type = $(bill).attr('name');
                var link = function() {
					return qz.printers.find(printer_name).then(function(printer) {
//								qz.printers.setPrinterCallbacks(function(evt) {
//									if(evt.statusCode != 0){
//										if(!error.includes(printer_name)){
//											error.push(printer_name);
//										}
//										var printer_error_name = '';
//										if(error.length){
//											if(error.length == 1){
//												if(error[0] == 'POS Order'){
//													printer_error_name = 'Không tìm thấy máy in Bill';
//				//									if(bill_type != 'kitchen-bill'){
//				//										printer_error_name = 'Không tìm thấy máy in bill';
//				//									}else{
//				//										printer_error_name = 'Không tìm thấy máy in label';
//				//									}
//												}else{
//													printer_error_name = 'Không tìm thấy máy in Label';
//												}
//											}else{
//												printer_error_name = 'Không tìm thấy máy in Bill và Label';
//											}
//				                            self.pos.gui.show_popup('alert',{
//				                                'title': 'ERROR',
//				                                'body':  printer_error_name,
//				                            });
//										}
//									}
//								});
	                            var options = {}
	                            if (printer_name == 'POS Label'){
	                                 options = {
	                                     margins: {
	                                         top: 0.05,
	                                         // right: 0.05,
	                                         // bottom: 0.05,
	                                         left: 0.05,
	                                     }
	                                 }
	                            }else{
									options = { margins: { top: 0, right: 0, bottom: 0, left: 0.0833333333 }};	
								}
	                            var config = qz.configs.create(printer, options);
	                            var data = [{
	                                type: 'pixel',
									format: 'html',
									flavor: 'plain',
	                                data: $(bill).html(),
	                            }];
								//Open cash when using cash payment method
								if (printer_name == 'POS Order' && bill_type != 'kitchen-bill' && !self.pos.config.use_replacement_printer && check_payment_cash){
									var data_kick_cashbox = ['\x10' + '\x14' + '\x01' + '\x00' + '\x05',];
									qz.print(config, data_kick_cashbox);
								}
	                            if(printer == 'POS Label'){
	                                config.config.scaleContent = true;
	                                config.config.rasterize = false;
	                                data[0].options = {
	                                    pageWidth: 1.97,
	                                    pageHeight: 1.18
	                                }
	                            }else{
									config.config.scaleContent = false;
					                config.config.rasterize = false;
					                data[0].options = {
					                    pageWidth: 2.85,
					                }
								}
	                            // clearTimeout(clearTimeout_vals);
//								qz.printers.startListening(printer).then(function(){
//						            // get the status
//						            qz.printers.getStatus().then(function() {
//						            });
//						        });
	                            return qz.print(config, data);
	                        }).catch(function(e) {
								if(!error.includes(printer_name)){
									error.push(printer_name);
								}
								var printer_error_name = '';
								if(error.length){
									if(error.length == 1){
										if(error[0] == 'POS Order'){
											printer_error_name = 'Không tìm thấy máy in Bill';
		//									if(bill_type != 'kitchen-bill'){
		//										printer_error_name = 'Không tìm thấy máy in bill';
		//									}else{
		//										printer_error_name = 'Không tìm thấy máy in label';
		//									}
										}else{
											printer_error_name = 'Không tìm thấy máy in Label';
										}
									}else{
										printer_error_name = 'Không tìm thấy máy in Bill và Label';
									}
									printer_error_name = "Khởi động lại QZ Tray và vào Lịch sử in lại bill."
		                            self.pos.gui.show_popup('alert',{
		                                'title': 'ERROR',
		                                'body':  printer_error_name,
		                            });
								}
	                        });
						}
						chain.push(link);
                    });
			var firstLink = new RSVP.Promise(function(r, e) { r(); });

		    var lastLink = null;
		    chain.reduce(function(sequence, link) {
		        lastLink = sequence.then(link);
		        return lastLink;
		    }, firstLink);
		
		    //this will be the very last link in the chain
		    lastLink.catch(function(err) {
		        console.error(err);
		    });
		},
        finalize_validation: function() {
            var self = this;
			var order = this.pos.get_order();
			var lines = self.pos.get_order().get_paymentlines();
			//Vuong: set currency_origin for payment
			_.each(lines, function(payment_line){
				var currency = self.pos.currency;
				var amount = payment_line.amount;
				var rate = 1;
				if(payment_line.payment_method.journal_type == 'bank' && self.pos.config.is_dollar_pos){
					currency = self.pos.company_currency;
					amount = payment_line.amount*self.pos.currency.rate;
					rate = currency.rate/self.pos.currency.rate;
				}
				if(!payment_line.currency_name){
					payment_line.set_currency(currency, amount, rate);
				}
			})
			this._super();
			if((order.has_printed_label_first || order.order_in_call_center) && this.pos.draft_order_count && this.pos.draft_order_count > 0){
				this.pos.draft_order_count -= 1;
			}
			var check_payment_cash = false;
			//Open cash when using cash payment method
			if (!self.pos.config.use_replacement_printer){
	    		for(var i=0; i<lines.length; i++){
	    			if(lines[i].payment_method.is_cash_count && lines[i].amount > 0){
	    				check_payment_cash = true;
	    				break;
	    			}
	    		}
			}
//            setTimeout(function(){
                if (self.pos.config.use_multi_printer){
                    if (!qz.websocket.isActive()){
						if(self.pos.config.use_replacement_printer && self.pos.config.printer_ip){
							qz.websocket.connect({host:self.pos.config.printer_ip}).then(function(){
								self.bill_print_qz(check_payment_cash);
							})
							.catch(function() {
								self.pos.gui.show_popup('alert',{
	                                'title': 'ERROR',
	                                'body':  'Khởi động lại QZ Tray và vào Lịch sử in lại bill.',
	                            });
				            });
						}else{
							qz.websocket.connect().then(function(){
								self.bill_print_qz(check_payment_cash);
							})
							.catch(function() {
								self.pos.gui.show_popup('alert',{
	                                'title': 'ERROR',
	                                'body':  'Khởi động lại QZ Tray và vào Lịch sử in lại bill.',
	                            });
				            });
						}
				    }else{
						self.bill_print_qz(check_payment_cash);
					}
                } else{
                    window.print();
                }
				//Vuong: Auto back to product screen after printing
				self.pos.get_order().finalize();
//            },1500);
        },
//        validate_order:function(force_validation){
//            var self = this;
//			if (!this.order_is_valid(force_validation)) {
//	            return;
//	        }
//			var order = this.pos.get_order();
//			var payment_line_exceed = order.check_payment_exceed_amount();
//			if (payment_line_exceed){
//				return this.pos.chrome.gui.show_popup('alert',{
//                    'title': 'Cảnh báo',
//                    'body':  'Thanh toán từ phương thức ' + payment_line_exceed.payment_method.name + ' đang dư tiền, vui lòng kiểm tra lại',
//                });
//			}
//            var start_year = this.pos.pos_session.start_at.split(' ')[0].split('-')[0];
//            var start_month = this.pos.pos_session.start_at.split(' ')[0].split('-')[1];
//            var start_day = this.pos.pos_session.start_at.split(' ')[0].split('-')[2];
//            var start_hour = this.pos.pos_session.start_at.split(' ')[1].split(':')[0];
//            var start_minute = this.pos.pos_session.start_at.split(' ')[1].split(':')[1];
//            var start_second = this.pos.pos_session.start_at.split(' ')[1].split(':')[2];
//            var session_start_date_obj = new Date(parseInt(start_year),parseInt(start_month)-1,parseInt(start_day),parseInt(start_hour),parseInt(start_minute),parseInt(start_second));
//            session_start_date_obj.setHours(session_start_date_obj.getHours() + 7);
//            var session_start_date = session_start_date_obj.format('Y-m-d');
//            var now_date = (new Date).format('Y-m-d');
//            // Thái: Không được validate đơn hàng nếu ca bán hàng được mở ngày hôm trước
//            if (session_start_date != now_date){
//                return this.pos.chrome.gui.show_popup('alert',{
//                    'title': 'ERROR',
//                    'body':  'Bạn cần phải đóng ca bán hàng ngày cũ để mở ca ngày mới !!!',
//                });
//            }
//            
//			var lines = this.pos.get_order().get_paymentlines();
//			for ( var i = 0; i < lines.length; i++ ) {
//	            if (lines[i].amount == 0) {
//	            	return this.gui.show_popup('alert',{
//		                'title': 'Cảnh báo',
//		                'body':  'Vui lòng xóa những dòng thanh toán có giá trị bằng 0',
//		            });
//	            }
//	        }
//            
//            var code = [];
//            var employee_payment = [];
//            var payment_has_employee_id = [];
//            var payment_line = order.paymentlines.models;
//    		for(var i in payment_line){
//    			//employee payment
//    			if(payment_line[i].payment_method.use_for=='on_account_emp' && payment_line[i].amount > 0 
//    			 && payment_line[i].employee_id && payment_line[i].max_on_account_amount > 0){
//    				employee_payment.push([payment_line[i].employee_id, payment_line[i].amount]);
//    				payment_has_employee_id.push(payment_line[i]);
//    			}
//    			//voucher_code
//    			if(payment_line[i].voucher_code){
//    				code.push([payment_line[i].voucher_code, 1]);
//    			}
//    		}
//    		
//    		var orderlines = order.get_orderlines();
//    		var partner_id = false;
//    		var partner = this.pos.get_client() || false;
//    		if(partner){
//    			partner_id = partner.id;
//    		}
//    		
////    		var code = order.coupon_code;
//    		var coupon_code_backend = []
//    		if(order.coupon_code_array.length){
//    			//unset current_coupon_code if coupon_code_array doesn't containt it
//    			if(order.current_coupon_code && !order.coupon_code_array.includes(order.current_coupon_code)){
//    				order.set_current_coupon_info('', 0, false);
//    			}
//    			for(var c in order.coupon_code_array){
//    				var used_count = 0;
//    	    		if(order.current_coupon_code && order.coupon_code_array[c] == order.current_coupon_code && order.current_coupon_limit && order.current_coupon_promotion){
//    	                for(var i = 0; i < orderlines.length; i++){
//    	                	if(orderlines[i].promotion_id && orderlines[i].promotion_line_id == order.current_coupon_promotion){
//    	                		used_count += orderlines[i].quantity;
//    	        			}
//    	                }
//    	    		}else{
//    	    			coupon_code_backend.push(order.coupon_code_array[c]);
//    	    			used_count = 1
//    	    		}
//    				code.push([order.coupon_code_array[c], used_count]);
//    			}
//    		}
//    		if(coupon_code_backend.length){
//    			order.coupon_code_list = coupon_code_backend.join(', ')
//    		}else{
//    			order.coupon_code_list = '';
//    		}
//    		var warehouse_id = self.pos.config.warehouse_id;
//            
//            //write reward code
//            if (order.reward_code && !order.done_reward_code){
//                rpc.query({
//                    model: 'pos.order',
//                    method: 'update_set_done_reward_code',
//                    args: [order.reward_code, order.name],
//                }).then(function(result_from_server){
//                    if(result_from_server == true){
//                        order.done_reward_code = order.reward_code;
//                        self.validate_order(force_validation);
//                    }else{
//                        order.reward_code = false;
//                        order.done_reward_code = false;
//                        self.gui.show_popup('error',{
//                            'title': _t('Error: Could not Save Changes'),
//                            'body': _t('Mã dự thưởng không hợp lệ hoặc đã được sử dụng'),
//                        });
//                    }
//                },function(error){
//					error.event.preventDefault();
//                    self.gui.show_popup('error',{
//                        'title': _t('Error: Could not Save Changes'),
//                        'body': _t('Your Internet connection is probably down.'),
//                    });
//                });
//            }else if(employee_payment.length){
//            	rpc.query({
//                    model: 'hr.employee',
//                    method: 'update_employee_on_account_amount',
//                    args: [employee_payment, order.name],
//                }).then(function(result_from_server){
//                    if(result_from_server == true){
//                        for(var pay in payment_has_employee_id){
//                        	payment_has_employee_id[pay].set_max_on_account_amount(0);
//                        }
//                        self.validate_order(force_validation);
//                    }else{
//                    	return self.gui.show_popup('alert',{
//                            'title': 'Cảnh báo',
//                            'body':  'Số tiền thanh toán vượt quá số tiền còn lại trong tài khoản: ' + self.format_currency(result_from_server) +  '. Vui lòng kiểm tra lại',
//                        });
//                    }
//                },function(error){
//					error.event.preventDefault();
//                    self.gui.show_popup('error',{
//                        'title': _t('Error: Could not Save Changes'),
//                        'body': _t('Your Internet connection is probably down.'),
//                    });
//                });
//            	
//            }else if (order.use_coupon && code != undefined && code.length > 0){
//    			rpc.query({
//                    model: 'sale.promo.header',
//                    method: 'update_set_done_coupon',
//                    args: [code, order.name, partner_id, warehouse_id[0]],
//                })
//    			.then(function(result_from_server){
//    				if(order.use_coupon){
//    					if(result_from_server == true){
//    						order.set_coupon_code('');
//    						order.use_coupon = false;
//    						order.trigger('change',order);
//    						self.validate_order(force_validation);
//    					}else{
//    						self.gui.show_popup('error',{
//    			                'title': _t('Error: Could not Save Changes'),
//    			                'body': _t('Coupon/Voucher không hợp lệ hoặc đã được sử dụng: ' + result_from_server),
//    			            });
//    					}
//    				}
//    			},function(error){
//					error.event.preventDefault();
//    				self.gui.show_popup('error',{
//    	                'title': _t('Error: Could not Save Changes'),
//    	                'body': _t('Your Internet connection is probably down.'),
//    	            });
//    	        });
//    		}else{
//            	if (this.order_is_valid(force_validation)) {
//                    this.finalize_validation();
//                }
////                self._super(force_validation);
//            }
//        },
        render_order: function() {
            var self = this;
            var order = this.pos.get_order();
            var partner = order ? order.get_client() : false;
            var partner_level = partner ? partner.loyalty_level_id : false;
            var level_name = partner ? order.get_loyalty_level_name_by_id(partner_level[0]) : '';
            var points_old      = (partner && !partner.card_code_pricelist_id && !partner.use_for_on_account) ? partner.total_point_act : 0;
            var points_won      = partner ? order.get_won_points() : 0;
            var points_spent    = partner ? order.get_spent_points() : 0;
            var points_total    = partner ? order.get_new_points() : 0;
            var discount_amount = order ? order.discount_amount : 0;
            var discount_lines = order ? order.get_total_discount() : 0;
            
			var surcharge = order.total_surcharge;
            var total     = order ? order.get_total_with_tax() : 0;
            var discount_amount = order ? order.discount_amount : 0;
            var discount_lines = order ? order.get_total_discount() : 0;
            var subtotal = total - discount_amount + discount_lines - surcharge
            var total_discount = discount_amount - discount_lines;
            if(order && order.sale_type_id){
            	var sale_type = this.pos.db.sale_type_ids[order.sale_type_id];
                if(sale_type && sale_type.show_original_subtotal){
                	subtotal = order.get_total_list_price();
                	total_discount = total - subtotal;
                }
            }

            var order = $(QWeb.render('Payment-Order', {
                widget:this,
                order: this.pos.get_order(),
                orderlines: this.pos.get_order().get_orderlines_groupby_combo(),
                client: this.pos.get_order().get_client(),
                level_name: level_name,
                points_old: points_old,
                points_won: points_won,
                points_spent: points_spent,
                points_total: points_total,
                total_discount: total_discount,
				subtotal:subtotal
            }));
            return order;
        },
    	click_paymentmethods: function(id) {
    		var self = this;
    		var order = this.pos.get_order();
			if(order.is_paid()){
				return this.pos.chrome.gui.show_popup('alert',{
	                'title': 'Cảnh báo',
	                'body':  'Đơn hàng đã thanh toán đủ tiền',
	            });
			}
    		var lines = this.pos.get_order().get_paymentlines();
    		var partner = this.pos.get_order().get_client() || false;
    		var cashregister = this.pos.payment_methods_by_id[id];
            if(cashregister.use_for_voucher == true){
            	if(order.check_origin_order() && !order.check_order_with_loyalty_discount() && !order.check_order_payment_on_account() && !(partner && partner.card_code_pricelist_id) && !order.check_has_reward_code()){
//            		order.reset_base_price(true);
//    				order.remove_current_discount();
//    				order.unset_promotion_for_coupon();
    				self.show();
    	        	return self.gui.show_popup('voucherinput',{
    	    	    	title: _t('Nhập mã Voucher để thanh toán'),
    	    	    	cashregister:cashregister,
    	    	    });
            	}else{
					if(order.linked_draft_order_be){
						return this.pos.chrome.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
			            });
					}
            		return self.gui.show_popup('confirm',{
            			'title':  _t('Sử dụng Voucher trên đơn hàng nguyên giá'),
                        'body':  _t('Nếu xác nhận sử dụng Voucher trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                        'confirm': function() {
							if(partner && partner.card_code_pricelist_id){
								order.set_client(null);
							}
                        	order.reset_base_price(true);
            				order.remove_current_discount();
            				order.unset_promotion_for_coupon();
							order.set_disable_loyalty_discount(true);
                        	order.remove_loyalty_discount();
							order.remove_combo_done();
							order.remove_order_payment_on_account();
            				self.show();
            	        	self.gui.show_popup('voucherinput',{
            	    	    	title: _t('Nhập mã Voucher để thanh toán'),
            	    	    	cashregister:cashregister,
            	    	    });
                        },
                    });
            	}
        	}else if(cashregister.use_for == 'on_account_emp'){
				if(order.check_order_payment_on_account()){
					return this.pos.chrome.gui.show_popup('alert',{
		                'title': 'Cảnh báo',
		                'body':  'Đơn hàng đã có thanh toán On Account',
		            });
				}
				if(order.check_origin_order() && !order.check_order_with_loyalty_discount() && !order.check_order_payment_voucher()){
//					order.reset_base_price(true);
//    				order.remove_current_discount();
//    				order.unset_promotion_for_coupon();
					self.show();
            		order.employee_cashregister = cashregister;
					order.set_check_scan_employee_payment(true);
					return self.gui.show_popup('cardscanner',{
		    	    	title: 'Xin hãy quẹt thẻ nhân viên vào máy quét',
		    	    }); 
            	}else{
					if(order.linked_draft_order_be){
						return this.pos.chrome.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
			            });
					}
            		return self.gui.show_popup('confirm',{
            			'title':  _t('Sử dụng On Account trên đơn hàng nguyên giá'),
                        'body':  _t('Nếu xác nhận sử dụng On Account trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                        'confirm': function() {
                        	order.reset_base_price(true);
            				order.remove_current_discount();
            				order.unset_promotion_for_coupon();
							order.set_disable_loyalty_discount(true);
                        	order.remove_loyalty_discount();
							order.remove_combo_done();
							order.remove_order_payment_voucher();
							self.show();
            				order.employee_cashregister = cashregister;
							order.set_check_scan_employee_payment(true);
							return self.gui.show_popup('cardscanner',{
				    	    	title: 'Xin hãy quẹt thẻ nhân viên vào máy quét',
				    	    }); 
                        },
                    });
            	}
        	}else if(cashregister.use_for == 'on_account_customer'){
				if(order.check_order_payment_on_account('on_account_emp')){
					return this.pos.chrome.gui.show_popup('alert',{
		                'title': 'Cảnh báo',
		                'body':  'Đơn hàng đã có thanh toán On Account',
		            });
				}
				if(order.check_origin_order_without_combo() && !order.check_order_with_loyalty_discount() && !order.check_order_payment_voucher()){
//					order.reset_base_price(true);
//    				order.remove_current_discount();
//    				order.unset_promotion_for_coupon();
					self.show();
            		order.partner_cashregister = cashregister;
					order.set_check_scan_partner_payment(true);
					return self.gui.show_popup('cardscanner',{
		    	    	title: 'Xin hãy quẹt thẻ khách hàng vào máy quét',
		    	    }); 
            	}else{
					if(order.linked_draft_order_be){
						return this.pos.chrome.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
			            });
					}
            		return self.gui.show_popup('confirm',{
            			'title':  _t('Sử dụng Thẻ trả trước trên đơn hàng nguyên giá'),
                        'body':  _t('Nếu xác nhận sử dụng Thẻ trả trước trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                        'confirm': function() {
                        	order.reset_base_price(true);
            				order.remove_current_discount();
            				order.unset_promotion_for_coupon();
							order.set_disable_loyalty_discount(true);
                        	order.remove_loyalty_discount();
//							order.remove_combo_done();
							order.remove_order_payment_voucher();
							self.show();
            				order.partner_cashregister = cashregister;
							order.set_check_scan_partner_payment(true);
							return self.gui.show_popup('cardscanner',{
				    	    	title: 'Xin hãy quẹt thẻ khách hàng vào máy quét',
				    	    }); 
                        },
                    });
            	}
        	}else if(cashregister.use_for == 'visa'){
				if(order.check_origin_order() && !order.check_order_with_loyalty_discount() && !order.check_order_payment_voucher() && !order.check_order_payment_on_account()){
//					order.reset_base_price(true);
//    				order.remove_current_discount();
//    				order.unset_promotion_for_coupon();
					self.show();
            		return self.gui.show_popup('textinput',{
		    	    	title: 'Vui lòng nhập đầu mã thẻ Visa',
		    	    	error: '',
		    	    	confirm: function(val) {
							if(!val){
								this.options.error = 'Vui lòng nhập đầu mã Visa';
								return self.gui.show_popup('textinput',this.options);
							}
							var code_valid = self.pos.payment_method_visa.filter(function(l){
								return l.payment_method_id[0] == cashregister.id && l.code == val;
							})
							if(!code_valid.length){
								this.options.error = 'Đầu mã Visa không hợp lệ';
								this.options.value = val;
								return self.gui.show_popup('textinput',this.options);
							}
							order.remove_all_order_payment();
							order.payment_promotion_id = cashregister.id;
							order.compute_promotion();
							order.add_paymentline(cashregister);
							order.select_paymentline(undefined);
    		    			self.reset_input();
                            self.render_paymentlines();
							self.show();														
		    	    	},
						cancel: function() {
							order.payment_promotion_id = false;
		    	    	},
		    	    });
            	}else{
					if(order.linked_draft_order_be){
						return this.pos.chrome.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
			            });
					}
            		return self.gui.show_popup('confirm',{
            			'title':  _t('Sử dụng khuyến mãi Visa trên đơn hàng nguyên giá'),
                        'body':  _t('Nếu xác nhận sử dụng khuyến mãi Visa trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
                        'confirm': function() {
                        	order.reset_base_price(true);
            				order.remove_current_discount();
            				order.unset_promotion_for_coupon();
							order.set_disable_loyalty_discount(true);
                        	order.remove_loyalty_discount();
							order.remove_combo_done();
							self.show();
//            				order.employee_cashregister = cashregister;
//							order.set_check_scan_employee_payment(true);
							return self.gui.show_popup('textinput',{
				    	    	title: 'Vui lòng nhập đầu mã thẻ Visa',
				    	    	error: '',
				    	    	confirm: function(val) {
									if(!val){
										this.options.error = 'Vui lòng nhập đầu mã Visa';
										return self.gui.show_popup('textinput',this.options);
									}
									var code_valid = self.pos.payment_method_visa.filter(function(l){
										return l.payment_method_id[0] == cashregister.id && l.code == val;
									})
									if(!code_valid.length){
										this.options.error = 'Đầu mã Visa không hợp lệ';
										this.options.value = val;
										return self.gui.show_popup('textinput',this.options);
									}
									order.remove_all_order_payment();
									order.payment_promotion_id = cashregister.id;
									order.compute_promotion();
									order.add_paymentline(cashregister);
									order.select_paymentline(undefined);
		    		    			self.reset_input();
		                            self.render_paymentlines();
									self.show();	
				    	    	},
								cancel: function() {
									order.payment_promotion_id = false;
				    	    	},
				    	    });
                        },
                    });
            	}
        	}else if(cashregister.use_for == 'cash' && self.pos.currencies.length > 1 && self.pos.config.is_dollar_pos){
                var list = [];
                for (var i = self.pos.currencies.length-1; i >= 0; i--) {
                    var origin_currency = self.pos.currency;
                	var currency = self.pos.currencies[i];
                    var currency_name = currency.name + ' (' + currency.symbol + ')';
                    var item_description = '';
                    if (currency.id != origin_currency.id){
						var currency_rate = currency.rate/self.pos.currency.rate;
                        var total2paid = order.get_total_with_tax() - order.get_total_paid();
                        item_description += (order.format_value((total2paid/currency_rate).toFixed(2)) + ' ' + currency.symbol);
                    }
                    list.push({
                        label: currency_name,
                        item:  currency,
                        description: item_description
                    });
                }
                return self.gui.show_popup('selection',{
                    'title': 'Vui lòng chọn tiền tệ thanh toán',
                    'list': list,
                    'confirm': function(currency){
                        var rate = 0;
                        var selected_currency = currency
                    	if(currency.id == self.pos.currency.id){
                            order.add_paymentline(cashregister);
//                            order.selected_paymentline.set_currency(selected_currency, 0, 1);
                    		self.reset_input();
                            self.render_paymentlines();
                    		return
                    	}
                    	if(self.pos.currency.id == self.pos.company_currency){
                    		rate = currency.rate
                    	}else{
                    		rate = currency.rate/self.pos.currency.rate;
                        }
                    	var rate_string = '(1 ' + currency.symbol + ' = ' + rate.toString() + self.pos.currency.symbol +')';
                    	self.gui.show_popup('numberinputwidget',{
          					'title': 'Nhập số tiền thanh toán ' + rate_string ,
          					'confirm': function(value) {
          						if (isNaN(value)){
          							if (typeof value =='string'){
          					    		value = value.replace(/,/g,'');
          					    	}
          						}
          						if (isNaN(value)){
      								self.gui.show_popup('error',_t('Vui lòng nhập đúng số tiền'));
          						}else {
            		              	var amount = value*rate;
            		              	order.add_paymentline(cashregister);
                                    order.selected_paymentline.set_amount(amount);
                                    order.selected_paymentline.set_currency(selected_currency, value, rate);
            		    			self.reset_input();
                                    self.render_paymentlines();
          						}
          					}
          				});
                    },
                });
        	}
            this._super(id);
        },
        payment_input: function(input) {
        	var self = this;
        	var order = this.pos.get_order();
        	var amount_total = order.get_total_with_tax();
            var paymentline = this.pos.get_order().selected_paymentline;

            // disable changing amount on paymentlines with running or done payments on a payment terminal
            if (this.payment_interface && !['pending', 'retry'].includes(paymentline.get_payment_status())) {
                return;
            }

            var newbuf = this.gui.numpad_input(this.inputbuffer, input, {'firstinput': this.firstinput});
            
            var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
            this.firstinput = (newbuf.length === 0);
            
            var oldbuff = this.inputbuffer;
            if(currency.name == "VND"){
                newbuf = newbuf.replace(/,/g,'');
                oldbuff = this.inputbuffer.replace(/,/g,'');
            }

            // popup block inputs to prevent sneak editing. 
            if (this.gui.has_popup()) {
                return;
            }
            
            if(paymentline && (paymentline.payment_method.use_for == 'on_account_emp' || paymentline.payment_method.use_for == 'on_account_customer') && newbuf){
            	var amount_to_paid = order.get_due(paymentline);
            	if(newbuf > paymentline.max_on_account_amount){
            		return this.pos.chrome.gui.show_popup('alert',{
                        'title': 'Cảnh báo',
                        'body':  'Số tiền thanh toán vượt quá số tiền còn lại trong tài khoản: ' + self.format_currency(paymentline.max_on_account_amount) +  '. Vui lòng kiểm tra lại',
                    });
            	}else if(newbuf > amount_to_paid){
            		return this.pos.chrome.gui.show_popup('alert',{
                        'title': 'Cảnh báo',
                        'body':  'Số tiền vượt quá mức cần thanh toán: ' + self.format_currency(amount_to_paid) +  '. Vui lòng kiểm tra lại',
                    });
            	}
            }
            
            if (newbuf !== oldbuff) {
                this.inputbuffer = newbuf;
                var order = this.pos.get_order();
                if (paymentline) {
                    var amount = this.inputbuffer;

                    if (this.inputbuffer !== "-") {
                        amount = field_utils.parse.float(this.inputbuffer);
                    }

                    paymentline.set_amount(amount);
                    this.render_paymentlines();
                    this.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(amount));
                }
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
			this.$('.set-label').click(function(){
                self.pos.chrome.screens.products.numpad.set_label_order('show_payment');
            });
            this.$('.print-label').click(function(){
                self.push_draft_order();
                $(this).addClass('printed');
            });
            var order = this.pos.get_order();
            if (order.linked_draft_order_be){
                self.$('.back').off();
            }
			if (self.pos.config.is_callcenter_pos){
				self.$('.paymentmethods-container').addClass('overlaypos');
				self.$('.list-item-numpad').addClass('overlaypos');
				self.$('.list-item-price').addClass('overlaypos');
				
            }
        },

		print_qz_label: function(){
			var self = this;
			var element2print = $('.label-content .pos-sale-ticket');
			var chain = [];
            _.each(element2print, function(bill){
                var printer_name = $(bill).attr('label');
				var link = function() {
	                return qz.printers.find(printer_name).then(function(printer) {
	                    var config = qz.configs.create(printer, {
	                        margins: {
	                            top: 0.15,
	                            // right: 0.05,
	                            // bottom: 0.05,
	                            left: 0.15,
	                        }
	                    });
	                    var data = [{
	                        type: 'pixel',
							format: 'html',
							flavor: 'plain',
	                        data: $(bill).html(),
	                    }];
	                    if(printer == 'POS Label'){
	                        config.config.scaleContent = true;
	                        config.config.rasterize = false;
	                        data[0].options = {
	                            pageWidth: 1.97,
	                            pageHeight: 1.18
	                        }
	                    }
	                    qz.print(config, data);
	                }).catch(function(e) {
	                    self.pos.gui.show_popup('alert',{
	                        'title': 'ERROR',
	                        'body':  'Khởi động lại QZ Tray và thử lại.',
	                    });
	                });
				}
				chain.push(link);
            });
			var firstLink = new RSVP.Promise(function(r, e) { r(); });

		    var lastLink = null;
		    chain.reduce(function(sequence, link) {
		        lastLink = sequence.then(link);
		        return lastLink;
		    }, firstLink);
		
		    //this will be the very last link in the chain
			if(lastLink){
				lastLink.catch(function(err) {
			        console.error(err);
			    });
			}
		},
        
        push_draft_order: function(){
            var self = this;
            var order = this.pos.get_order();
            if (order.has_printed_label_first){
                return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Label đã được in ra. Bạn không thể in lại lần nữa',
                });
            }
            if (!self.pos.config.use_multi_printer){
                return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Máy POS chưa được cấu hình để in trước Label. Vui lòng liên hệ Quản trị viên.',
                });
            }
			order.has_printed_label_first = true;
			if(!order.order_in_call_center){
				self.pos.draft_order_count += 1;
	            order.linked_draft_order_be = order.name;
	            order.state = 'draft';
	            self.pos.push_order(order, {'draft': true});
	            self.$('.back').off();
			}
            var order_html = QWeb.render('label',{
                widget: this,
                order:order,
                orderlines:order.get_orderlines()
            });
            var contents = self.$el[0].querySelector('.label-content');
            contents.innerHTML = order_html;
//			console.log($('.label-content .pos-sale-ticket').html());
			if (!qz.websocket.isActive()){
				if(self.pos.config.use_replacement_printer && self.pos.config.printer_ip){
					qz.websocket.connect({host:self.pos.config.printer_ip}).then(function(){
						self.print_qz_label();
					})
					.catch(function() {
						self.pos.gui.show_popup('alert',{
                            'title': 'ERROR',
                            'body':  'Khởi động lại QZ Tray và vào Lịch sử in lại bill.',
                        });
		            });
				}else{
					qz.websocket.connect().then(function(){
						self.print_qz_label();
					})
					.catch(function() {
						self.pos.gui.show_popup('alert',{
                            'title': 'ERROR',
                            'body':  'Khởi động lại QZ Tray và vào Lịch sử in lại bill.',
                        });
		            });
				}
			}else{
				self.print_qz_label();
			}
			
        },
        render_paymentlines: function() {
            var self  = this;
            var order = this.pos.get_order();
            if (!order) {
                return;
            }

            var lines = order.get_paymentlines();
            var due   = order.get_due();
            var extradue = 0;
            if (due && lines.length  && due !== order.get_due(lines[lines.length-1]) && due>0) {
                extradue = due;
            }

            this.$('.paymentlines-container').empty();
            var lines = $(QWeb.render('PaymentScreen-PaymentlinesCustom', { 
                widget: this, 
                order: order,
                paymentlines: lines,
                extradue: extradue,
            }));

            lines.on('click','.delete-button',function(){
                self.click_delete_paymentline($(this).data('cid'));
            });

            lines.on('click','.paymentline',function(){
                self.click_paymentline($(this).data('cid'));
            });
                
            lines.appendTo(this.$('.paymentlines-container'));
			
			this.$('.paymentmethods-container').empty();
			var methods = this.render_paymentmethods();
        	methods.appendTo(this.$('.paymentmethods-container'));
        },
		
		click_paymentline: function(cid){
	        var lines = this.pos.get_order().get_paymentlines();
	        for ( var i = 0; i < lines.length; i++ ) {
	            if (lines[i].cid === cid) {
	            	if(lines[i].payment_method.use_for=='visa'){
						return;
//						return this.gui.show_popup('alert',{
//	                        'title': 'ERROR',
//	                        'body':  'Vui lòng không chỉnh sửa thanh toán Visa',
//	                    });
	            	}
	            }
	        }
			this._super(cid);
	    },

		click_delete_paymentline: function(cid){
			var self = this;
			var order = this.pos.get_order();
	        var lines = order.get_paymentlines();
	        for ( var i = 0; i < lines.length; i++ ) {
	            if (lines[i].cid === cid) {
	            	if(lines[i].payment_method.use_for=='visa'){
	            		return self.gui.show_popup('confirm',{
	                        'title': 'Cảnh báo',
	                        'body': 'Nếu huỷ thanh toán Visa, các khuyến mãi liên quan sẽ không còn khả dụng',
	                        'confirm': function(){
								order.payment_promotion_id = false;
								order.reset_base_price(true);
    							order.remove_current_discount();
//								order.compute_promotion();
	                            order.remove_paymentline(lines[i]);
				                self.reset_input();
				                self.render_paymentlines();
								self.show();
	                        }
	                    })
	            	}
	            }
	        }
			this._super(cid);
			this.show();
	    },
    });
    
    var HistoryOrdesScreenWidget = screens.ScreenWidget.extend({
        template: 'HistoryOrdesScreenWidget',

        auto_back: true,
		
        click_back: function() {
            var self = this;
            var order = this.pos.get_order();
            self.gui.show_screen('products');
            order.unset_order_to_return();
        },
        show: function(options){
            var self = this;
			var order = this.pos.get_order();
            this._super();
//			this.query_method = 'get_order_by_query';
			this.sort_mode = 'none';
    
            this.renderElement();
			$('.title-name.label').text('Label');

            this.$('.back').click(function(){
                self.click_back();
            });

            this.$('.re-print-bill').click(function(){
                self.re_print_bill();
            });
            this.$('.payment-bill').click(function(){
//                self.click_back();
                self.pay_draft_order($(this).data('name'));
				self.$('.payment-bill').off('click');
            });
			
			//Vuong: Sort list by amount_total
			this.$('.title-name.amount-total').click(function(){
                self.sort_by_amount_total();
            });

            this.$('.order-list-contents').on('click', '.order-line', function(event){
				self.$('.record-body').removeClass("history-record-highlight");
    			$(this).addClass("history-record-highlight");
                var clear_timeout = null;
                clearTimeout(clear_timeout);
                if ($(this).hasClass('draft')){
                    self.$('.payment-bill').removeClass('oe_hidden');
                    self.$('.re-print-bill').addClass('oe_hidden');
                    $('.pos-return-container').empty();
                    self.$('.payment-bill').attr('data-name',$(this).data('name'));
                } else{
                    self.preview_order($(this).data('name'));
//                    clear_timeout = setTimeout(function(){
//                        self.$('.re-print-bill').removeClass('oe_hidden');
//                        self.$('.payment-bill').addClass('oe_hidden');
//                    }, 2000);
                }
            });
    
            var search_timeout = null;
    
            if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
                this.chrome.widget.keyboard.connect(this.$('.searchbox input'));
            }
    
            this.$('.searchbox input').on('input',function(event){
                clearTimeout(search_timeout);
                var searchbox = this;
                search_timeout = setTimeout(function(){
                    self.perform_search(searchbox.value, event.which === 13);
                },70);
            });
    
            this.$('.searchbox .search-clear').click(function(){
                self.clear_search();
            });
            var session_id = this.pos.pos_session.id;
            if (session_id){
                rpc.query({
                    model: 'pos.order',
                    method: order.history_query_method,
                    args: ['',session_id],
                }).then(function(vals){
                    self.render_list(vals);
                })
            }else{
                this.render_list([]);
            }
        },
		get_order_draft_by_uid: function(uid) {
	        var orders = this.pos.get_order_list();
	        for (var i = 0; i < orders.length; i++) {
	            if (orders[i].uid == uid || orders[i].linked_draft_order_be == uid) {
	                return orders[i];
	            }
	        }
	        return undefined;
	    },
        pay_draft_order: function(name){
            var self = this;
			//Vuong: Show order if it exist
			var order_existed = this.get_order_draft_by_uid(name);
			
			if(order_existed){
				this.pos.set_order(order_existed);
				return;
			}
//            var order = self.pos.add_new_order();
			var new_order = new models.Order({},{pos:this.pos});
        	this.pos.get('orders').add(new_order);

            rpc.query({
                model: 'pos.order',
                method: 'get_order_to_pay',
                args: [name],
            }).then(function(vals){
                self.import_draft_order(new_order, vals.order, vals.orderlines);
            })
        },
        set_order_with_json: function(json_order){
            var self = this;
            var order = self.pos.get_order();
            var json = order.export_as_JSON();
            var advoid_update = ['name','sequence_number', 'pos_session_id', 'lines', 'payment_ids', 'statement_ids', 'uid', 'user_id', 'sale_type_name', 'creation_date']
            for (var key in json){
                if (advoid_update.indexOf(key) >= 0) {
                    continue
                }
                if (typeof(json_order[key]) == 'object' && key != 'coupon_code_array'){
                    order[key] = json_order[key][0];
                    if(key == 'sale_type_id'){
                        order['sale_type_name'] = json_order[key][1];
                    }
                } else{
                    order[key] = json_order[key];
                }
            }
            order.coupon_code_array = [];
            order.coupon_code_list = '';
            order.server_id = json_order['id'];
			order.pay_draft_order = true;
			if(json_order['coupon_code'] && json_order['coupon_code'] != ''){
				var coupon_code_array = json_order['coupon_code'].split(', ');
				_.each(coupon_code_array, function(code){
					order.set_coupon_code(code);
				})
				if(order.coupon_code_array){
					order.use_coupon = true;
				}
			}
        },
        set_order_lines_w_json: function(json_orderlines){
            var self = this;
            var order = self.pos.get_order();
            _.each(json_orderlines, function(line_json){
                var product_id = line_json.product_id[0];
                var product = self.pos.db.product_by_id[product_id];
                var order_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
                var order_line_json = order_line.export_as_JSON();
                var advoid_update = [
                ]
                for (var key in order_line_json){
                    if (advoid_update.indexOf(key) >= 0) {
                        continue
                    }
                    if (typeof(line_json[key]) == 'object' && key){
                        order_line[key] = line_json[key][0];
                    } else {
                        order_line[key] = line_json[key];
                    }
                }
                // if(order_line['combo_id'] || ){
                //     order_line.set_price(order_line['price_unit']);
                // }

                // Set topping name:
//                var topping_lines = json_orderlines.filter(function(item){
//                    return item.is_topping_line && item.related_line_id == line_json.fe_uid
//                })
//                var topping_list_name = [];
//                if(topping_lines.length){
//                	for(var tp in topping_lines){
//            			var topping_product = topping_lines[tp];
//            			var topping_price_fm = order.format_currency_no_symbol(topping_product.price_unit);
//            			var topping_price_str = topping_price_fm.toString();
//						var topping_product_obj = self.pos.db.product_by_id[topping_product.product_id[0]];
//            			var name_with_price = topping_product_obj.display_name + ' x ' + topping_price_str;
//            			topping_list_name.push(name_with_price);
//                	}
//                }
//                if(topping_list_name.length){
//            		var topping_name = topping_list_name;
//            		order_line.set_topping_name(topping_name);
//            	}else{
//            		order_line.set_topping_name(false);
//            	}
				
				var material_list_name = [];
				//Set cup type
				if(order_line.product.fnb_type == 'drink'){
					var cup_type_default = order.get_default_cup_by_product(order_line.product);
					var cup_name = '';
					if(order_line.cup_type == 'plastic'){
						if(cup_type_default == 'paper_1st' || cup_type_default == 'paper'){
							cup_name = 'Ly nhựa';
						}
    				}else if(order_line.cup_type == 'paper'){
						if(cup_type_default == 'plastic_1st' || cup_type_default == 'plastic'){
    						cup_name = 'Ly giấy';
						}
	    			}else{
	    				cup_name = 'Không lấy Ly';
					}
					if(cup_name != ''){
        				material_list_name.push(cup_name);
        			}
				}
				
				//Set materiral 
				if(line_json.option_ids.length){
					var material = line_json.option_ids;
                	for(var ml in material){
//            			var material_product = self.pos.db.get_product_by_id(material[ml].option_id);
						var material_product = self.pos.db.material_ids[material[ml].option_id];
            			var material_name = material_product.name;
            			if(material[ml].option_type == 'none'){
            				material_list_name.push('Không ' + material_name);
            			}else if(material[ml].option_type == 'below'){
            				material_list_name.push('Ít ' + material_name);
            			}else if(material[ml].option_type == 'over'){
            				material_list_name.push('Nhiều ' + material_name);
            			}
                	}
                	order_line.set_custom_material_list(material);
                }
                
                if(material_list_name.length){
            		var material_name_display = material_list_name.join(', ');
            		order_line.set_material_name(material_list_name);
            	}else{
            		order_line.set_material_name([]);
            	}
                order_line.set_quantity_no_compute(line_json.qty);
				order_line.id = order_line.fe_uid;
                order_line.set_price(line_json.price_unit);
                order_line['uom_id'] = line_json['uom_id'][0];
//				if(line_json.loyalty_discount_percent){
//					order_line.set_loyalty_discount(line_json.loyalty_discount_percent);
//				}
                self.pos.get_order().orderlines.add(order_line);
            })
        },
        import_draft_order: function(order, json_order, json_orderlines){
            var self = this;
			self.pos.set_order(order);
			if(json_order['partner_id']){
				var client = this.pos.db.get_partner_by_id(json_order['partner_id'][0]);
				if(client){
					order.set_client(client);
				}
			}
            self.set_order_lines_w_json(json_orderlines);
            self.set_order_with_json(json_order);
            self.gui.show_screen('payment');
        },
        preview_order: function(name){
            var self = this;
            var order = this.pos.get_order();
            order.unset_order_to_return();
            $('.pos-return-container').empty();
//            order.get_order_to_return(name, 'return');
			self.$('.re-print-bill').addClass('oe_hidden');
	    	var gui_order = self.pos.chrome.gui;
	    	rpc.query({
	            model: 'pos.order',
	            method: 'get_order_by_name',
	            args: [name],
	        }).then(function(vals){
				if (vals[0]){
					order.set_values_to_return(vals);
					self.render_receipt();
					self.$('.re-print-bill').removeClass('oe_hidden');
                    self.$('.payment-bill').addClass('oe_hidden');
	        	}else{
	        		gui_order.show_popup('error',{
	                    'title': _t('Error'),
	                    'body': _t('Không tìm thấy hoá đơn trong hệ thống !!'),
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
        hide: function () {
            this._super();
        },
        perform_search: function(query, associate_result){
            var self = this;
			var order = this.pos.get_order();
            var session_id = this.pos.pos_session.id;
			var orderby = 'date_order desc';
			if(this.sort_mode == 'desc'){
				orderby = 'amount_total desc';
			}else if(this.sort_mode == 'asc'){
				orderby = 'amount_total asc';
			}
            if (session_id){
                rpc.query({
                    model: 'pos.order',
                    method: order.history_query_method,
                    args: [query,session_id,orderby],
                }).then(function(vals){
                    self.render_list(vals);
                })
            }else{
                this.render_list([]);
            }
        },
        clear_search: function(){
            this.render_list([]);
            this.$('.searchbox input')[0].value = '';
            this.$('.searchbox input').focus();
        },
        render_list: function(orders){
            var contents = this.$el[0].querySelector('.order-list-contents');
            contents.innerHTML = "";
			this.orders = orders;
            if (orders){
                for(var i = 0, len = orders.length; i < len; i++){
                    var order    = orders[i];
                    var date_order_fm = order.date_order;
                    var date_order_year = date_order_fm.split(' ')[0].split('-')[0];
                    var date_order_month = date_order_fm.split(' ')[0].split('-')[1];
                    var date_order_day = date_order_fm.split(' ')[0].split('-')[2];
                    var date_order_hour = date_order_fm.split(' ')[1].split(':')[0];
                    var date_order_minute = date_order_fm.split(' ')[1].split(':')[1];
                    var date_order_second = date_order_fm.split(' ')[1].split(':')[2];
                    var date_order_obj = new Date(parseInt(date_order_year),parseInt(date_order_month)-1,parseInt(date_order_day),parseInt(date_order_hour),parseInt(date_order_minute),parseInt(date_order_second));
                    date_order_obj.setHours(date_order_obj.getHours() + 7);
                    var date_order_fm = date_order_obj.format('d/m/Y H:i');
                    order.date_order = date_order_fm;
                    var orderline_html = QWeb.render('HistoryOrderLine',{widget: this, order:order});
                    var orderline = document.createElement('tbody');
                    orderline.innerHTML = orderline_html;
                    orderline = orderline.childNodes[1];
                    contents.appendChild(orderline);
                }
            }
        },
        render_receipt: function() {
            var self = this;
            var order = this.pos.get_order();
            var order_to_return = order.order_to_return[0];
			if(!order_to_return){
				return;
			}
            var order_id = order_to_return.order;
            var date_order_fm = order_id.date_order;
            var date_order_year = date_order_fm.split(' ')[0].split('-')[0];
            var date_order_month = date_order_fm.split(' ')[0].split('-')[1];
            var date_order_day = date_order_fm.split(' ')[0].split('-')[2];
            var date_order_hour = date_order_fm.split(' ')[1].split(':')[0];
            var date_order_minute = date_order_fm.split(' ')[1].split(':')[1];
            var date_order_second = date_order_fm.split(' ')[1].split(':')[2];
            var date_order_obj = new Date(parseInt(date_order_year),parseInt(date_order_month)-1,parseInt(date_order_day),parseInt(date_order_hour),parseInt(date_order_minute),parseInt(date_order_second));
            date_order_obj.setHours(date_order_obj.getHours() + 7);
            var date_order_fm = date_order_obj.format('d/m/Y H:i');

            var amount_before_discount = order_id.amount_total - order_id.discount_amount;
            var amount_with_tax = amount_before_discount + order_id.amount_tax;
            var amount_tax = order_id.amount_tax;
            var percent_discount = 0;
            if(order_id.discount_amount!=0){
                percent_discount = round_pr(-order_id.discount_amount/amount_before_discount*100,1);
            }
            
            var cashier_name = order_to_return.cashier;
            var partner =  this.pos.db.get_partner_by_id(order_id.partner_id);
            order_id.partner_return_id = false;
            if(partner){
                order_id.partner_return_id = partner;
                var partner_name = partner.name;
                var partner_mobile = partner.mobile;
                var partner_ref = partner.ref || false;
            }
            var orderlines = order_to_return.orderlines;
            
            for(var line in orderlines){
                var product = this.pos.db.get_product_by_id(orderlines[line].product_id);
                var unit_id = product.uom_id;
                if(!unit_id){
                    return undefined;
                }
                var product_uom = unit_id[1];
                orderlines[line].product_name = product.display_name;
                orderlines[line].product_uom = product_uom;
                orderlines[line].default_code = product.default_code;
                orderlines[line].new_price = orderlines[line].price_subtotal_incl/orderlines[line].qty;
            }
            var receipt_return = {
                    cashier_name:cashier_name,
                    amount_before_discount:amount_before_discount,
                    amount_with_tax:amount_with_tax,
                    partner_name:partner_name,
                    partner_mobile:partner_mobile,
                    partner_ref:partner_ref,
                    amount_tax:amount_tax,
                    date_order_fm:date_order_fm,
                    percent_discount:percent_discount,
            };
            $('.pos-return-container').html(QWeb.render('PosReturnTicket',{
                    widget:this,
                    order: order_id,
                    current_order:order,
                    receipt: order.export_for_printing(),
                    receipt_return: receipt_return,
                    orderlines: _.sortBy(orderlines, 'id', 'asc'),
                    paymentlines: order_to_return.paymentlines,
                }));
            var count = parseInt(order_id.number_of_printed_bill);
            self.$('#number_count').html(count);
        },

		print_bill_qz: function(){
			var self = this;
			var bills = $('.body-bill.pos-return-container .pos-sale-ticket');
            _.each(bills, function(bill){
                var printer_name = $(bill).attr('label');
                qz.printers.find(printer_name).then(function(printer) {
                    var options = { margins: { top: 0, right: 0, bottom: 0, left: 0.0833333333 }};
                    // if (printer_name == 'POS Label'){
                    //     options = {
                    //         margins: {
                    //             // top: 0.15,
                    //             // right: 0.05,
                    //             // bottom: 0.05,
                    //             left: 0.15,
                    //         }
                    //     }
                    // }
                    var config = qz.configs.create(printer, options);
                    var data = [{
                        type: 'pixel',
						format: 'html',
						flavor: 'plain',
                        data: $(bill).html()
                    }];  // Raw ZPL
					config.config.scaleContent = false;
	                config.config.rasterize = false;
	                data[0].options = {
	                    pageWidth: 2.85,
	                }
                    qz.print(config, data);
                }).catch(function(e) {
                    self.pos.gui.show_popup('alert',{
                        'title': 'ERROR',
                        'body':  'Khởi động lại QZ Tray và thử lại',
                    });
                });
            })
		},

        re_print_bill: function() {
            var self = this;
            if(this.pos.get_order().order_to_return){
                var order = this.pos.get_order().order_to_return[0].order;
                var count = parseInt(order.number_of_printed_bill);
                order.number_of_printed_bill+=1;
                self.$('#number_count').html(count+1);
                self.$('#lasted-print').html(moment().format('L LT'));
                rpc.query({
                    model:'pos.order',
                    method: 'set_count_of_print_bill',
                    args: [order.name],
                })
            }
//            this.pos.get_order()._printed = true;
            if (self.pos.config.use_multi_printer){
				if (!qz.websocket.isActive()){
					if(self.pos.config.use_replacement_printer && self.pos.config.printer_ip){
						qz.websocket.connect({host:self.pos.config.printer_ip}).then(function(){
							self.print_bill_qz();
						})
						.catch(function() {
							self.pos.gui.show_popup('alert',{
                                'title': 'ERROR',
                                'body':  'Khởi động lại QZ Tray và thử lại.',
                            });
			            });
					}else{
						qz.websocket.connect().then(function(){
							self.print_bill_qz();
						})
						.catch(function() {
							self.pos.gui.show_popup('alert',{
                                'title': 'ERROR',
                                'body':  'Khởi động lại QZ Tray và thử lại',
                            });
			            });
					}
				}else{
					self.print_bill_qz();
				}
            } else{
                setTimeout(function(){
                    window.print()
                },1500);
            }
        },
		sort_by_amount_total: function(){
			if(!this.orders || !this.orders.length){
				$('.fa-sort-up').addClass('oe_hidden');
				$('.fa-sort-down').addClass('oe_hidden');
				return;
			}
			if(this.sort_mode == 'desc'){
				this.sort_mode = 'asc';
				if($('.fa-sort-up').hasClass('oe_hidden')){
					$('.fa-sort-up').removeClass('oe_hidden');
					$('.fa-sort-down').addClass('oe_hidden');
				}
				var orders = _.sortBy(this.orders,function(line){return line.amount;});
				this.render_list(orders);
			}else{
				this.sort_mode = 'desc';
				if($('.fa-sort-down').hasClass('oe_hidden')){
					$('.fa-sort-down').removeClass('oe_hidden');
					$('.fa-sort-up').addClass('oe_hidden');
				}
				var orders = _.sortBy(this.orders,function(line){return line.amount;}).reverse();
				this.render_list(orders);
			}
		},
    });
    gui.define_screen({
        'name':'historyOrders',
        'widget': HistoryOrdesScreenWidget,
        'condition': function(){
            return true;
        },
    });
    screens.ActionpadWidget.include({
    	init: function(parent, options) {
            var self = this;
            this._super(parent, options);

            this.pos.unbind('change:selectedClient');
        },
        
        get_promotion: function(){
        	var self = this;
			var order = this.pos.get_order();
        	var orderlines = order.get_orderlines();

			var numpad = self.chrome.screens.products.numpad;
			numpad.set_reward_code();
        	
    		if (orderlines.length ==0) {
        		return this.gui.show_popup('error',_t('Vui lòng chọn sản phẩm'));
        	}
    		
    		var total_employee_coupon_qty = 0;
    		if(order.current_coupon_code && order.coupon_code_array.includes(order.current_coupon_code) && order.current_coupon_limit && order.current_coupon_promotion){
                for(var i = 0; i < orderlines.length; i++){
                	if(orderlines[i].promotion_id && orderlines[i].promotion_line_id == order.current_coupon_promotion){
                		total_employee_coupon_qty += orderlines[i].quantity;
        			}
                }
                if(total_employee_coupon_qty > order.current_coupon_limit){
                	return this.gui.show_popup('alert',{
                        'title': 'Cảnh báo',
                        'body':  'Số lượng Coupon khả dụng còn lại là ' + order.current_coupon_limit.toString() + '. Vui lòng kiểm tra lại',
                    })
                }
    		}
			
			//raise for coupon product
			for (var i=0; i < orderlines.length; i++){
				if(orderlines[i].cup_type == 'themos' && orderlines[i].product_coupon_code && orderlines[i].coupon_promotion_limit){
					var total_qty = 0;
					var line_related = orderlines.filter(function(l){
						return l.cup_type == 'themos' && l.product_coupon_code == orderlines[i].product_coupon_code;
					})
					_.each(line_related, function(line){
						total_qty += line.quantity;
					})
					if(total_qty > orderlines[i].coupon_promotion_limit){
						return this.gui.show_popup('alert',{
	                        'title': 'Cảnh báo',
	                        'body':  'Số lượng Coupon khả dụng còn lại là ' + orderlines[i].coupon_promotion_limit.toString() + '. Vui lòng kiểm tra lại',
	                    })
					}
				}
			}
    		
    		self.gui.show_screen('payment');
        },
    });
    
    //Barcode scanner
    BarcodeReader.include({
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
    	scan: function(code){
    		var self = this;
            if (!code) {
                return;
            }
            code = self.get_special_card_code(code);
            var order = this.pos.get_order();
            var current_popup = this.pos.gui.current_popup || false;
			//return on payment screen
			if(self.pos.gui.get_current_screen() == 'payment' && !current_popup){
				return;
			}
    		if(order.check_scan_card_customer){
                order.set_customer_by_code(code);
    		}else if(order.check_keyboard_customer){
    			var check_store_manager = order.check_employee_code(code);
    			if(check_store_manager){
    				var history_value = {
						'date_perform':(new Date).format('Y-m-d H:i:s'),
						'type': 'search_customer',
						'pos_manager_id': check_store_manager
					}
		        	order.set_operation_history_list(history_value);
    				return self.pos.chrome.gui.show_screen('clientlist');
    			}
    		}else if(order.check_create_customer){
    			var check_store_manager = order.check_employee_code(code);
    			if(check_store_manager){
					current_popup.click_confirm();
					return self.pos.chrome.screens.clientlist.display_client_details('edit',{
		                'country_id': self.pos.company.country_id,
	//	                'state_id': self.pos.company.state_id,
		            });
    			}
    		}else if(order.check_scan_manual_discount){
    			var check_store_manager = order.check_employee_code(code);
    			if(check_store_manager){
    				return self.pos.chrome.screens.products.numpad.get_discount_info();
    			}
    		}else if(order.check_scan_open_cashbox){
    			var check_store_manager = order.check_employee_code(code);
    			if(check_store_manager){
    				var history_value = {
						'date_perform':(new Date).format('Y-m-d H:i:s'),
						'type': 'open_cash',
						'pos_manager_id': check_store_manager
					}
		        	order.set_operation_history_list(history_value);
    				order.open_cashdrawer_via_socket('POS Order');
    				current_popup.click_confirm();
    			}
    		}else if(order.check_scan_employee_coupon){
    			var check_employee = order.check_employee_code(code, false);
    			if(check_employee){
    				var coupon_code = ({code:code});
    				order.get_coupon_by_code(coupon_code,'coupon', true);
    			}
    		}else if(order.check_scan_employee_payment){
    			var check_employee = order.check_employee_code(code, false);
    			if(check_employee){
    				var employee_by_id = self.pos.employee_by_id[check_employee];
    				order.get_payment_by_employee(employee_by_id);
    				current_popup.click_confirm();
    			}
    		}else if(order.check_scan_partner_payment){
				order.get_payment_by_partner(code);
//				current_popup.click_confirm();
    		}else if(order.check_scan_change_cashier){
    			var check_employee = order.check_employee_code(code, false);
    			if(check_employee){
    				var employee_by_id = self.pos.employee_by_id[check_employee];
                    if(!employee_by_id.use_for_employee_coupon){
    				    order.change_cashier(employee_by_id);
    				    current_popup.click_confirm();
                    } else {
                        return self.pos.chrome.gui.show_popup('error',{'body':'Mã thẻ nhân viên không tồn tại'});
                    }
    			}
    		}else if(current_popup && current_popup.popup_voucher){
    			current_popup.show_popup_voucher(code);
    		}else if(current_popup && current_popup.popup_coupon){
    			current_popup.click_confirm();
    		}else{
    			this._super(code);
    		}
        },
    });

	chrome.OrderSelectorWidget.include({
		deleteorder_click_handler: function(event, $el) {
	        var self = this;
	        var order = this.pos.get_order();
	        if(order.has_printed_label_first){
	        	return this.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Đơn hàng đã in label không thể xoá',
                })
	        }else{
				this._super(event, $el);
			}
		},
		renderElement: function() {
            this._super();
            var self = this;
//            $('.handle-tab').click(function () {
//                const _self = $(this);
//                $('.handle-tab').removeClass('active show');
//                _self.tab('show');
//            })
            var $carousel_1 = $('.custom-carousel-1').owlCarousel({
                loop: false,
                margin: 5,
                nav: true,
                dots: false,
                autoWidth:true,
                items: 3,
                responsiveClass:true,
                navText: ['<img src="/phuclong_pos_theme/static/src/img/w_arrow_left.png" />','<img src="/phuclong_pos_theme/static/src/img/w_arrow_right.png" />'],
                responsive: {
                    0: {
                        items: 3
                    },
        
                    1024: {
                        items: 3
                    },
        
                    1375: {
                        items: 3
                    }
                }
            })
			var sequence_current = this.pos.get_order().sequence_number - this.pos.get_order_list()[0].sequence_number;
			sequence_current = sequence_current ? sequence_current-1 : 0;
			$('.custom-carousel-1').trigger("to.owl.carousel", [sequence_current, 0, true]);
        
            $('.wrap-center-menu .owl-next').click(function() {
                refreshCarousel();
            })
            $('.wrap-center-menu .owl-prev').click(function() {
                refreshCarousel();
            })
            
            function refreshCarousel() {
                $carousel_1.data('owl.carousel')._invalidated.width = true;
                $carousel_1.trigger('refresh.owl.carousel');
            };
            
            var nav = $('#tabProduct .owl-nav');
            var tabProduct = $('#tabProduct');
            if(nav.hasClass('disabled')) {
                tabProduct.removeClass('has-nav');
            } else {
                tabProduct.addClass('has-nav');
            }
        },
	});
	
	chrome.UsernameWidget.include({
		renderElement: function(){
            var self = this;
            this._super();
            this.$el.off('click');
			$('#user-name').html(this.pos.get_cashier().name);
        },
		start: function() {
            this._super();
            var self = this;
            $('.fullscreen').click(function () {
				if (!document.fullscreenElement) {
					self.openFullscreen();
				}
                if($('.fullscreen-exit').hasClass('oe_hidden')){
					$('.fullscreen-exit').removeClass('oe_hidden');
					$('.fullscreen').addClass('oe_hidden');
				}
            });
			$('.fullscreen-exit').click(function () {
				if (document.fullscreenElement) {
					self.closeFullscreen();
				}
                if($('.fullscreen').hasClass('oe_hidden')){
					$('.fullscreen').removeClass('oe_hidden');
					$('.fullscreen-exit').addClass('oe_hidden');
				}
            })
			//chrome cast
			$('.cast-off').click(function () {
				if (!self.pos.db.presentationConnected) {
					self.start_cast_external_display();
				}
            });
			$('.cast-on').click(function () {
				if (self.pos.db.presentationConnected) {
					self.stop_cast_external_display();
				}
            })
			$('.name-user').click(function(){
                self.click_username();
            });
			$('.config-printer').click(function(){
                self.config_printer();
            });
		},
		config_printer: function(){
			return this.show_popup_config_printer();
		},
//		connect_qz_from_ip: function(ip){
//			var self = this;
//			qz.websocket.connect({host: ip}).then(function() {
//				self.update_pos_config_printer(ip);
//				return self.gui.show_popup('alert',{
//                    'title': 'Thông báo',
//                    'body':  'Kết nối thành công tới IP ' + ip,
//                });
//			}).catch(function(e) {
//				return self.show_popup_config_printer('Địa chỉ IP không hợp lệ, vui lòng kiểm tra lại', ip)
//            });
//		},
		show_popup_config_printer: function(error=false, value=false) {
        	var self = this;
        	var order = self.pos.get_order();
        	if(!value){
        		value = self.pos.config.printer_ip;
        	}
        	this.gui.show_popup('textinput',{
    	    	title: 'Nhập địa chỉ IP máy in thay thế',
    	    	value: value,
    	    	error: error,
    	    	confirm: function(ip) {
//					if(ip && ip.length < 7){
//						return self.show_popup_config_printer('Địa chỉ IP có độ dài chỉ tối thiểu là 7 kí tự', ip)
//					}
					if(ip == self.pos.config.printer_ip && qz.websocket.isActive()){
						return;
					}
					if(!ip){
						if (qz.websocket.isActive()){
					        qz.websocket.disconnect().then(function() {
								qz.websocket.connect();
							})
					    }else{
							qz.websocket.connect();
						}
						self.update_pos_config_printer(false);
					}else{
//						if (qz.websocket.isActive()){
//					        qz.websocket.disconnect().then(function() {
//								qz.websocket.connect({host: ip});
//							})
//					    }else{
//							qz.websocket.connect({host: ip});
//						}
//						self.update_pos_config_printer(ip);
//						return self.gui.show_popup('alert',{
//		                    'title': 'Thông báo',
//		                    'body':  'Kết nối thành công tới IP ' + ip,
//		                });
						try {
							var http = new XMLHttpRequest();
							http.open("GET", "//" + ip + ":" + '8181', /*async*/true);
							http.timeout = 500;
							http.onreadystatechange = function() {
								if (this.readyState === 4) {
									if(this.status == 200){
										if (qz.websocket.isActive()){
									        qz.websocket.disconnect().then(function() {
												qz.websocket.connect({host: ip});
											})
									    }else{
											qz.websocket.connect({host: ip});
										}
										self.update_pos_config_printer(ip);
										return self.gui.show_popup('alert',{
						                    'title': 'Thông báo',
						                    'body':  'Kết nối thành công tới IP ' + ip,
						                });
									}else{
										return self.show_popup_config_printer('Địa chỉ IP không hợp lệ, vui lòng kiểm tra lại', ip)
									}
								}
							};
						    http.send(null);
					  	} catch(exception) {
					    	return self.show_popup_config_printer('Địa chỉ IP không hợp lệ, vui lòng kiểm tra lại', ip)
					  	}
    	    		}
    	    	},
    	    });
        },
		update_pos_config_printer: function(ip){
			var self = this;
			rpc.query({
                model: 'pos.config',
                method: 'update_pos_config_printer',
                args: [self.pos.config.id, ip],
            }).then(function(result){
				if(result){
					self.pos.config.use_replacement_printer = ip ? true : false;
					self.pos.config.printer_ip = ip;
				} 
//                self.renderElement();
            },function(error){
				error.event.preventDefault();
                self.pos.chrome.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': _t('Your Internet connection is probably down.'),
                });
            });
		},
        click_username: function(){
            var self = this;
			var order = this.pos.get_order();
			if(!self.pos.config.update_cashier_to_session){
				return;
			}
			if(self.pos.config.use_barcode_scanner_to_open_session){
				order.set_check_scan_change_cashier(true);
	        	return self.gui.show_popup('cardscanner',{
	    	    	title: 'Xin hãy quẹt thẻ nhân viên để chỉnh sửa thông tin Thu ngân'
	    	    });
			}else{
				var list = [];
		        this.pos.employee_by_id.forEach(function(employee) {
                    if(!employee.use_for_employee_coupon){
                        list.push({
                            'label': employee.name,
                            'item':  employee,
                        });
                    }
		        });
				var current_cashier_id = self.pos.pos_session.cashier_id[0];
		
		        self.gui.show_popup('selection', {
	                title: 'Đổi thu ngân',
	                list: list,
	                is_selected: function (employee) {
	                    return employee.id === current_cashier_id;
	                },
					confirm: function (employee_selected){
						order.change_cashier(employee_selected);
					}
	            });
			}
        },
		get_cashier_name: function(){
			return this.pos.pos_session.cashier_id[1];
		},
		//Vuong: fullscreen button
		openFullscreen: function(){
			var elem = document.documentElement;
			if (elem.requestFullscreen) {
			    elem.requestFullscreen();
			} else if (elem.mozRequestFullScreen) { /* Firefox */
			    elem.mozRequestFullScreen();
			} else if (elem.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
			    elem.webkitRequestFullscreen();
			} else if (elem.msRequestFullscreen) { /* IE/Edge */
			    elem.msRequestFullscreen();
			}
		},
		closeFullscreen: function(){
			if (document.exitFullscreen) {
			    document.exitFullscreen();
			} else if (document.mozCancelFullScreen) { /* Firefox */
			    document.mozCancelFullScreen();
			} else if (document.webkitExitFullscreen) { /* Chrome, Safari and Opera */
			    document.webkitExitFullscreen();
			} else if (document.msExitFullscreen) { /* IE/Edge */
			    document.msExitFullscreen();
			}
		},
		start_cast_external_display: function(){
			return;
		},
		stop_cast_external_display: function(){
			return;
		},
	});
	
    return {
        HistoryOrdesScreenWidget: HistoryOrdesScreenWidget,
    };
});