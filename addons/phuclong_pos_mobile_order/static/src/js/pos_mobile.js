odoo.define('phuclong_pos_mobile_order.pos_mobile', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var _t = core._t;
    var gui = require('point_of_sale.gui');
	var PosConnection = require('pos_longpolling.connection');
	var PosDB = require('point_of_sale.DB');
	var HistoryOrdesScreenWidget = require('phuclong_pos_theme.templates').HistoryOrdesScreenWidget;
    
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this,arguments);
//			this.partner_expired_date = this.partner_expired_date || false;
        },
		export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
//			json.partner_expired_date = partner_expired_date;
            return json;
        },
        init_from_JSON: function(json){
            _super_order.init_from_JSON.apply(this,arguments);
//            this.partner_expired_date = json.partner_expired_date;
        },
    });

	HistoryOrdesScreenWidget.include({
		import_draft_order: function(order, json_order, json_orderlines){
            var self = this;
			if(json_order.order_in_app){
				if(!self.pos.db.sale_type_ids[json_order.sale_type_id[0]]){
					return self.pos.chrome.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Sale type Mobile chưa được thiết lập trên điểm bán hàng này',
	                });
				}
			}
			this._super(order, json_order, json_orderlines)
        },
		set_order_with_json: function(json_order){
            var self = this;
			this._super(json_order)
            var order = self.pos.get_order();
			if(json_order.order_in_app){
				order.linked_draft_order_be = json_order.name;
				order.order_in_app = json_order.order_in_app;
				order.name = json_order.name;
				order.payment_name = json_order.payment_name;
				order.delivery_address = json_order.delivery_address;
				order.mobile_receiver_info = json_order.mobile_receiver_info;
				if(json_order.mobile_receiver_info){
					order.mobile_receiver_info_raw  = json_order.mobile_receiver_info.replace('Người nhận: ','');
				}
				order.description_for_app = json_order.description_for_app;
				if(json_order.date_order){
					var date_order_mobile = new Date(json_order.date_order);
					date_order_mobile.setHours(date_order_mobile.getHours() + 8);
					date_order_mobile = date_order_mobile.format('d-m-Y H:i:s');
					order.date_order_mobile = date_order_mobile;
				}
			}
        },
	});

	screens.NumpadWidget.include({
        renderElement: function() {
        	var self = this;
            this._super();
            var button_mobile_order = this.$el.find('.mobile-order');
			if(self.pos.mobile_order_list.length){
				button_mobile_order.addClass('has-mobile-order').text('ĐH Mobile (' + self.pos.mobile_order_list.length + ')');
			}else{
				button_mobile_order.removeClass('has-mobile-order').text('ĐH Mobile');
			}
            $(button_mobile_order).parent().click(function(){
				if(self.pos.config.is_callcenter_pos){
					return self.gui.show_popup('alert',{
			              'title': 'ERROR',
			              'body':  'Không sử dụng chức năng này tại POS Call Center',
			        });
				}
            	self.clickShowMoblieOrder();
            })
        },
		clickShowMoblieOrder: function(){
			var self = this;
			var order = this.pos.get_order();
			order.history_query_method = 'get_mobile_order_by_query';
            self.gui.show_screen('historyOrders');
		}
	}),
	
	screens.ProductCategoriesWidget.include({
		change_mobile_status: function(bool){
			var self = this;
			rpc.query({
                model: 'pos.order',
                method: 'change_mobile_status',
                args: [self.pos.config.id, bool],
            }).then(function(){
				self.pos.config.use_for_mobile = bool;
				self.renderElement(false, false, true);
            },function(error){
				error.event.preventDefault();
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': _t('Your Internet connection is probably down.'),
                });
            });
		},
        renderElement: function(show_combo=false, combo_coupon_id=false, render_from_combo_button=false){
            var self = this;
            this._super(show_combo, combo_coupon_id, render_from_combo_button);
            $('.btn-on-mobile').click(function(){
				return self.gui.show_popup('confirm',{
                    'title': 'Cảnh báo',
                    'body':  'Bạn chắc chắn muốn Bật nhận đơn hàng từ Mobile App?',
					'confirm': function(){
		                self.change_mobile_status(true);
		            },
                });
            });

            $('.btn-off-mobile').click(function(){
				return self.gui.show_popup('confirm',{
                    'title': 'Cảnh báo',
                    'body':  'Bạn chắc chắn muốn Tắt nhận đơn hàng từ Mobile App?',
					'confirm': function(){
		                self.change_mobile_status(false);
		            },
                });
			});
		},
	}),
	
	screens.PaymentScreenWidget.include({
		renderElement: function() {
            var self = this;
            this._super();
            var order = this.pos.get_order();
            if (order.order_in_app){
                self.$('.back').off();
				self.$('.paymentmethods-container').addClass('overlaypos');
				self.$('.list-item-numpad').addClass('overlaypos');
				self.$('.list-item-price').addClass('overlaypos');
				self.$('.message').text('Nhập Label để hoàn thành đơn hàng Mobile')
				
            }
        },
		validate_order:function(force_validation){
            var self = this;
			var order = this.pos.get_order();
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
            // Thái: Không được validate đơn hàng nếu ca bán hàng được mở ngày hôm trước
            if (session_start_date != now_date){
                return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'ERROR',
                    'body':  'Bạn cần phải đóng ca bán hàng ngày cũ để mở ca ngày mới !!!',
                });
            }
			if(order.order_in_app){
				if(!order.get_note_label()){
					self.chrome.screens.products.numpad.set_label_order();
					return;
	        	}
				rpc.query({
                    model: 'pos.order',
                    method: 'check_mobile_order',
                    args: [order.name],
                }).then(function(result_from_server){
                    if(result_from_server == true){
                        self.finalize_validation();
						var button_mobile_order = $('.mobile-order');
						if(self.pos.mobile_order_list && self.pos.mobile_order_list.includes(order.name)){
							self.pos.mobile_order_list = self.pos.mobile_order_list.filter(function(l){
								return l !=  order.name;
							})
						}
						if(self.pos.mobile_order_list.length){
							button_mobile_order.text('ĐH Mobile (' + self.pos.mobile_order_list.length + ')');
						}else{
							var button = button_mobile_order.parent();
							button_mobile_order.text('ĐH Mobile');
							button.removeClass('has-mobile-order');
						}
                    }else{
                        return self.gui.show_popup('confirm',{
                            'title': 'Cảnh báo',
                            'body':  'Đơn hàng đã bị huỷ, không thể tiếp tục xử lý',
							'confirm': function(){
				                self.pos.delete_current_order();
				            },
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
			}else{
				this._super(force_validation);
			}
        }
	}),

	PosDB.include({
//		load: function(store,deft){
//	        if(this.cache[store] !== undefined){
//	            return this.cache[store];
//	        }
//	        var data = localStorage[this.name + '_' + store];
//	        if(data !== undefined && data !== 'undefined' && data !== ""){
//	            data = JSON.parse(data);
//	            this.cache[store] = data;
//	            return data;
//	        }else{
//	            return deft;
//	        }
//	    },
	});
    
	var _super_pos_model = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
	    initialize: function(session, attributes) {
			var self = this;
	        this.on_syncing = false;
			this.mobile_order_list = [];
			var result = _super_pos_model.initialize.call(this,session,attributes);
	        return result;
	    },
		after_load_server_data: function () {
	        var self = this;
	        var session_id = this.pos_session.id;
			rpc.query({
	            model: 'pos.order',
	            method: 'check_mobile_draft_order',
	            args: [session_id],
	        }).then(function(vals){
	            if(vals && vals.length){
					self.mobile_order_list = vals;
					var button_mobile_order = $('.mobile-order');
					var button = button_mobile_order.parent();
					button_mobile_order.text('ĐH Mobile (' + vals.length + ')');
					button.addClass('has-mobile-order');
				}
	        })
	        return _super_pos_model.after_load_server_data.call(this);
	    },
		delete_current_order: function(){
			var self = this;
	        var order = this.get_order();
			_super_pos_model.delete_current_order.call(this);
	        if (order.order_in_app) {
				if(self.mobile_order_list && self.mobile_order_list.includes(order.name)){
					self.mobile_order_list = self.mobile_order_list.filter(function(l){
						return l !=  order.name;
					})
				}
	            this.reset_mobile_order_status();
	        }
	    },
	    receiver_message: function(message){
	    	var error = false;
			if(message && Array.isArray(message)){
				if(message[0] == 'mobile'){
					try{
						this.mobile_order_list = message[1];
						this.reset_mobile_order_status();
			        }catch(err){
			            console.log(error);
			        }
				}
			}
			_super_pos_model.receiver_message.call(this, message);
	    },
		reset_mobile_order_status: function(){
			var self = this;
			var button_mobile_order = $('.mobile-order');
			if(button_mobile_order.length){
				var button = button_mobile_order.parent();
				if(this.mobile_order_list.length){
					button_mobile_order.text('ĐH Mobile (' + this.mobile_order_list.length + ')');
					button.addClass('has-mobile-order');
				}else{
					button_mobile_order.text('ĐH Mobile');
					button.removeClass('has-mobile-order');
				}
			}	
		}
	});    
	
});

