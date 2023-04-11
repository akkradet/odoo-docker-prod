odoo.define('phuclong_pos_presentation.templates', function (require) {
    "use strict";
    var screens = require('point_of_sale.screens');
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

    var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');
	var utils = require('web.utils');
	var rpc = require('web.rpc');
	var models = require('point_of_sale.models');
	var chrome = require('point_of_sale.chrome');
	
	PosDB.include({
		init: function(options){
	        options = options || {};
            this.presentationRequest = this.presentationRequest || false;
            this.presentationConntection = this.presentationConntection || false;
            this.presentationConnected = this.presentationConnected || false;
            this.presentationConnectionId = this.presentationConnectionId || false;
	        this._super(options);
        },
    });
    var search_timeout = null;
    var count2ClosePresentPopup = 0;
    var display_availability = false;
    var check_display_availabity = 0;
	var check_set_present = false;

    screens.ScreenWidget.include({
        show: function() {
            var self = this;
            this._super();
            if(this.pos.config.use_external_display && !check_set_present){
				check_set_present = true;
				if(!self.pos.db.presentationConnected && self.pos.db.load('presentationConnectionId')){
					const presentationRequest = new PresentationRequest(['/web/presentation/receiver?config='+ self.pos.config_id]);
					presentationRequest.addEventListener('connectionavailable', function(event) {
	                    self.pos.db.presentationConnection = event.connection;
	                    self.pos.db.presentationConnection.addEventListener('close', function() {
	                        self.pos.db.presentationConnected = false;
	                    });
	                    self.pos.db.presentationConnection.addEventListener('terminate', function() {
	                        self.pos.db.presentationConnected = false;
	                        self.pos.db.save('presentationConnectionId', false);
							self.chrome.widget.username.renderElement();
							self.chrome.widget.username.start();
	                    });
	                });
					self.pos.db.presentationRequest = presentationRequest;
	                self.start_present();
	            }
                $('.pos').click(function(){
					try {
	                    self.present_order()
					}catch(err) {
						return;
					}
                })
            }
        },
		present_order: function(){
			var self = this;
			clearTimeout(search_timeout);
            if (self.pos.db.presentationConnected){
                var max_timeout = self.pos.config.order_break_timeout*1000 || 20000;
                self.send_present_order_detail(self.pos.db.presentationConnection);
                search_timeout = setTimeout(function(){
                    self.reset_present(self.pos.db.presentationConnection);
                }, max_timeout);
            }
		},
        start_present: function(){
            var self = this;
            if(self.pos.db.load('presentationConnectionId')){
                this.pos.db.presentationRequest.reconnect(self.pos.db.load('presentationConnectionId')).then(connection => {
                    this.pos.db.presentationConnected = true;
                    this.presentationConnection = connection;
                    this.pos.db.presentationConnectionId = connection.id
                    self.pos.db.save('presentationConnectionId', connection.id);
					self.chrome.widget.username.renderElement();
					self.chrome.widget.username.start();
					connection.send('reset');
                }).catch(error => {
                    this.pos.db.presentationConntected = false;
                    this.pos.db.presentationConnectionId = false;
					self.pos.db.save('presentationConnectionId', false);
                    this.pos.db.presentationRequest = false
					self.chrome.widget.username.renderElement();
					self.chrome.widget.username.start();
                });
            } else{
                this.pos.db.presentationRequest.start().then(connection => {
                    this.pos.db.presentationConnected = true;
                    this.presentationConnection = connection;
                    this.pos.db.presentationConnectionId = connection.id
                    self.pos.db.save('presentationConnectionId', connection.id);
                    count2ClosePresentPopup = 0;
					self.chrome.widget.username.renderElement();
					self.chrome.widget.username.start();
					connection.send('reset');
                }).catch(error => {
                    this.pos.db.presentationConntected = false;
                    this.pos.db.presentationConnectionId = false;
                    this.pos.db.presentationRequest = false
					self.chrome.widget.username.renderElement();
					self.chrome.widget.username.start();
                });
            }
        },
        reset_present: function(presentationConnection){
            var message = 'reset';
			if(presentationConnection){
				try{
					presentationConnection.send(message);
				}catch(err) {
					return;
				}
			}
        },
        send_present_order_detail: function(presentationConnection){
            // var message = 'reset';
            if(presentationConnection){
	            var message = this.render_order_to_present();
				try{
	            	presentationConnection.send(message);
				}catch(err) {
					console.log(err);
					return;
				}
			}
        },
        render_order_to_present: function() {
            var self = this;
            var order = this.pos.get_order();
            var partner = order ? order.get_client() : false;
            var partner_level = partner ? partner.loyalty_level_id : false;
            var level_name = partner ? order.get_loyalty_level_name_by_id(partner_level[0]) : '';
            var points_old      = partner ? partner.total_point_act : 0;
            var points_won      = partner ? order.get_won_points() : 0;
            var points_spent    = partner ? order.get_spent_points() : 0;
            var points_total    = partner ? order.get_new_points() : 0;
            var discount_amount = order ? order.discount_amount : 0;
            var discount_lines = order ? order.get_total_discount() : 0;
            var total_discount = discount_amount - discount_lines;
			var orderlines_to_present = this.pos.get_order().get_orderlines_groupby_combo();
			var orderlines_to_present_limit = [];
//			var start_from_line = 0;
//			if(orderlines_to_present.length > 15){
//				start_from_line = orderlines_to_present.length - 15;
//			}
//			for(var i=start_from_line; i < orderlines_to_present.length; i++){
//				orderlines_to_present_limit.push(orderlines_to_present[i]);
//			}
			var order_line = this.pos.get_order().get_orderlines_no_topping()
            var total_quantity = 0;
            _.each(order_line, function(line){
                if(line.product.default_code != 'reward_code'){
                    total_quantity+=line.quantity;
                }
            });
			var total_line = 15;
			for(var i=orderlines_to_present.length-1; i >= 0; i--){
				var orderlines = []
				if(orderlines_to_present[i].combo){
					total_line -= 1;
					orderlines = orderlines_to_present[i].lines;
				}else{
//					total_line -= 1;
					orderlines.push(orderlines_to_present[i].lines);
				}
				
				_.each(orderlines, function(l){
					total_line -= 1;
					if(l.promotion_id || l.promotion_all_order_id || l.material_name){
						total_line -= 0.5;
					}
					var topping_list = l.get_topping_list(true)
					if(topping_list.length){
						total_line -= 0.5*topping_list.length;
					}
				})
				if(total_line<=0){
					break;
				}
				orderlines_to_present_limit.push(orderlines_to_present[i]);
			}
			var reward_noti = ''
			var partner = this.pos.get_order().get_client()
			if(partner && this.pos.get_order().get_available_rewards().length){
				reward_noti = 'Bạn có quà tặng thẻ thành viên ' + level_name;
			}
			orderlines_to_present_limit = orderlines_to_present_limit.reverse()
            var order = $(QWeb.render('Present-Order', {
                widget:this,
                order: this.pos.get_order(),
                orderlines: orderlines_to_present_limit,
                client: partner,
                level_name: level_name,
                points_old: points_old,
                points_won: points_won,
                points_spent: points_spent,
                points_total: points_total,
				reward_noti: reward_noti,
                total_discount: total_discount,
				total_quantity: total_quantity,
            }));
//			if($(order).find('.present-order-scroll')){
//				$(order).find('.present-order-scroll').scrollTop(100 * this.pos.get_order().get_orderlines().length);
//			}
            var res = '';
            for(var i=0;i<order.length; i++){
                res+= order[i].outerHTML;
            }
            return res.replace(/undefined/g, '');
        },
    });

	chrome.UsernameWidget.include({
		start_cast_external_display: function(){
			var self = this;
			try{
				const presentationRequest = new PresentationRequest(['/web/presentation/receiver?config='+ self.pos.config_id]);
	            presentationRequest.addEventListener('connectionavailable', function(event) {
	                self.pos.db.presentationConnection = event.connection;
	                self.pos.db.presentationConnection.addEventListener('close', function() {
	                    self.pos.db.presentationConnected = false;
	                });
	                self.pos.db.presentationConnection.addEventListener('terminate', function() {
	                    self.pos.db.presentationConnected = false;
	                    self.pos.db.save('presentationConnectionId', false);
						self.chrome.widget.username.renderElement();
						self.chrome.widget.username.start();
	                });
	            });
	            navigator.presentation.defaultRequest = presentationRequest;
	            presentationRequest.getAvailability().then(availability => {
	                display_availability =  availability.value;
	                availability.addEventListener('change', function() {
	                    display_availability =  availability.value;
	                });
	            }).catch(error => {
	                display_availability = false;
	            });
                if (!self.pos.db.presentationRequest){
                    count2ClosePresentPopup++
                }
                self.pos.db.presentationRequest = presentationRequest;
                if(check_display_availabity <2){
                    self.chrome.screens.products.start_present();
                }
//				clearTimeout(search_timeout);
//	            if (self.pos.db.presentationConnected){
//	                var max_timeout = self.pos.config.order_break_timeout*1000 || 20000;
//	                self.chrome.screens.products.send_present_order_detail(self.pos.db.presentationConnection);
//	                search_timeout = setTimeout(function(){
//	                    self.chrome.screens.products.reset_present(self.pos.db.presentationConnection);
//	                }, max_timeout);
//	            }
			}catch(err) {
				return self.pos.chrome.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Kết nối màn hình phụ không khả dụng',
                })
			}
		},
		stop_cast_external_display: function(){
			this.pos.db.presentationConnection.terminate();
			return;
		},
	});
});
