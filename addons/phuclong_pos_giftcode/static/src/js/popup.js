odoo.define('phuclong_pos_giftcode.popups', function (require) {
    "use strict";
    var PopupWidget = require('point_of_sale.popups');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var PosDB = require('point_of_sale.DB');

    models.load_models([
        {
            model: 'giftcode.api.config',
            fields: [],
            loaded: function(self,api_configs){
                self.db.api_configs = api_configs;
            },
        },
        {
            model: 'giftcode.api.config.method',
            fields: [],
            loaded: function(self,api_config_methods){
                self.db.api_config_methods = api_config_methods;
            },
        },
		{
            model: 'giftcode.api.store',
            fields: [],
            loaded: function(self,api_config_stores){
                self.db.api_config_stores = api_config_stores;
            },
        },
    ]);
    PosDB.include({
		init: function(options){
	        options = options || {};
			this.api_configs = [];
			this.api_config_methods = [];
			this.api_config_stores = [];
	        this._super(options);
        },
    });
    var GiftcodeInputPopupWidget = PopupWidget.extend({
        template: 'GiftcodeInputPopupWidget',
        show: function(options){
            var self = this;
            options = options || {};
            this._super(options);
            this.renderElement();
            $('.confirm-giftcode').click(function () {
                self.click_confirm_giftcode();
            })
        },
		click_confirm: function(){
        	this.click_confirm_giftcode();
        },
        click_confirm_giftcode: function(){
            var self = this;
            var value = this.$('input,textarea').val();
			value = value.toUpperCase();
			value = value.replace(/ /g,'')
            var order = this.pos.get_order();
			var lines = order.get_paymentlines();
			for(var i=0; i<lines.length; i++){
    			if(lines[i].voucher_code && lines[i].voucher_code == value){
    				return self.gui.show_popup('error', 'Giftcode đã được nhập');
    			}
    		}
            this.gui.close_popup();
			if(value.length <= 0){
                return this.gui.show_popup('error',_t('Vui lòng nhập Giftcode'));
            }
			var domain = [['voucher_code','=', value],['payment_method_id','=', self.options.cashregister.id]];
            rpc.query({
                model: 'pos.payment',
                method: 'search',
                args: [domain],
            }).then(function (payment) {
                if (payment && payment.length) {   
                    return self.gui.show_popup('error', 'Giftcode đã được sử dụng ở đơn hàng trước đó');
                } else {
                    self.validate_giftcode(value);
                }
            },function(error){
				error.event.preventDefault();
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': _t('Your Internet connection is probably down.'),
                });
            });
        },
        validate_giftcode: function(value){
            var self = this;
            if(value.length <= 0){
                return this.gui.show_popup('error',_t('Vui lòng nhập Giftcode'));
            } else{
				value = value.toUpperCase();
                var giftcode_api = self.pos.db.api_configs.filter(function(item){
                    return item.id == self.options.cashregister.giftcode_api[0];
                })
                if (giftcode_api){
                    var validate_method = this.pos.db.api_config_methods.filter(function(item){
                        return item.api_config_id[0] == giftcode_api[0].id && item.type == 'validate'
                    })
                    if(validate_method){
						var store_id = giftcode_api[0].brand_id;
						var warehouse_id = self.pos.config.warehouse_id;
						if(giftcode_api[0].store_mapping_type == 'one2one'){
							var store_config = self.pos.db.api_config_stores.filter(function(item){
		                        return item.store_conf_id && item.store_conf_id[0] == giftcode_api[0].id && item.store_id[0] == warehouse_id[0];
		                    })
							if(store_config.length){
								store_id = store_config[0].gifcode_store_id;
							}
						}
						//signing
						var private_key = '-----BEGIN RSA PRIVATE KEY-----\n'+
										  giftcode_api[0].sec_key +
										  '\n-----END RSA PRIVATE KEY-----';
//						var sign = new JSEncrypt({default_key_sign:2048});
//						sign.setPrivateKey(private_key);
                        switch(giftcode_api[0].type){
							case "giftpop":
                                var body = {
                                    'authKey': giftcode_api[0].access_key,
									'brandCode': giftcode_api[0].branch_code,
                                    'pinNo': value,
									'storeCode': store_id.toString(),
                                };
								
								rpc.query({
					                model: 'pos.order',
					                method: 'make_signature_api',
					                args: [private_key, JSON.stringify(body)],
					            }).then(function (signature) {
					                var request = new XMLHttpRequest();
	                                request.open('POST', validate_method[0].api_url);
									request.setRequestHeader('Content-Type', 'application/json');
//									var signature = sign.sign(JSON.stringify(body), CryptoJS.SHA256, "sha256");
									request.setRequestHeader('Signature', signature);
	                                request.onreadystatechange = function () {
	                                    if (this.readyState === 4) {
	                                        var res;
	                                        try {
	                                            res = JSON.parse(this.responseText);
	//											console.log(res)
	                                        } catch(err) {
												if(this.responseText == ""){
													return self.gui.show_popup('alert',{
										                'title': 'Cảnh báo',
										                'body':  'Kết nối API thất bại',
										            });
												}
	                                            var lines = this.responseText.split('\n');
	                                            var json_array = '';
	                                            $.each(lines, function(item, vals){
	                                                if (vals.indexOf('email') >= 0){
	                                                    return
	                                                }
	                                                var text = vals;
	                                                if (vals.indexOf('//') >= 0){
	                                                    var text = vals.split('//')[0];
	                                                }
	                                                json_array += text;
	                                            })
	                                            res = JSON.parse(json_array);
	                                        }
											if(res.length==1){
												res = res[0];
											}
											var order = self.pos.get_order();
											//log response
											var data = {'giftcode_type':giftcode_api[0].type,
													'type':'validate',
													'order_name':order.name,
													'request_string':JSON.stringify(body),
													'response_string':JSON.stringify(res)}
											rpc.query({
								                model: 'giftcode.api.response',
								                method: 'create',
								                args: [data],
								            })
	                                        if (res.resCode != '0000' || (res.pinStatus != 'R' && res.pinStatus != 'U')){
												return self.gui.show_popup('alert',{
									                'title': 'Thanh toán không thành công',
									                'body':  res.message,
									            });
	                                        } else{
	//                                            var order = self.pos.get_order();
	                                            var amount2paid =  order.get_total_with_tax() - order.get_total_paid();
	                                            var amount_paid_by_gifcode = res.listPrice;
	                                            if (res.listPrice > amount2paid){
	                                                amount_paid_by_gifcode = amount2paid;
	                                            }
	                                            var cashregister = self.options.cashregister;
	                                            if(order.check_origin_order()){
	                                                order.reset_base_price(true);
	                                                order.remove_current_discount();
	                                                order.unset_promotion_for_coupon();
	                                                order.add_paymentline( cashregister );
													order.selected_paymentline.api_voucher_amount = res.listPrice;
	                                                order.selected_paymentline.set_amount(amount_paid_by_gifcode);
	                                                order.selected_paymentline.set_voucher_code(value);
	                                                order.selected_paymentline.use_api_giftcode(true);
	                                                order.use_coupon = true;
	                                                self.gui.current_screen.sort_payment_line()
	                                                self.gui.current_screen.show()
	                                            }else{
													if(order.linked_draft_order_be){
														return self.gui.show_popup('alert',{
											                'title': 'Cảnh báo',
											                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
											            });
													}
	                                                return self.gui.show_popup('confirm',{
	                                                    'title':  _t('Sử dụng Giftcode trên đơn hàng nguyên giá'),
	                                                    'body':  _t('Nếu xác nhận sử dụng Giftcode trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
	                                                    'amount': amount_paid_by_gifcode,
	                                                    'cashregister': cashregister,
	                                                    'confirm': function() {
	                                                        order.reset_base_price(true);
	                                                        order.remove_current_discount();
	                                                        order.unset_promotion_for_coupon();
															order.remove_combo_done();
															amount2paid =  order.get_total_with_tax() - order.get_total_paid();
															amount_paid_by_gifcode = res.listPrice
			                                                if (res.listPrice > amount2paid){
			                                                    amount_paid_by_gifcode = amount2paid;
			                                                }
	                                                        order.add_paymentline( this.options.cashregister );
	                                                        order.selected_paymentline.set_amount(amount_paid_by_gifcode);
	                                                        order.selected_paymentline.set_voucher_code(value);
	                                                        order.selected_paymentline.use_api_giftcode(true);
	                                                        order.use_coupon = true;
	                                                        self.gui.current_screen.sort_payment_line()
	                                                        self.gui.current_screen.show()
	                                                    },
	                                                });
	                                            }
	                                        }
	                                    }
	                                };
	                                setTimeout(function() {
	                                    request.send(JSON.stringify(body));
	                                }, 500);
					            },function(error){
									error.event.preventDefault();
					                self.gui.show_popup('error',{
					                    'title': _t('Error: Could not Save Changes'),
					                    'body': _t('Your Internet connection is probably down.'),
					                })
								});
                                break;
                            case "urbox":
                                var body = {
									'amount': 0,
                                    'app_id': giftcode_api[0].agent_site,
									'app_secret': giftcode_api[0].access_key,
//									'brand_code': '',
                                    'code': value,
									'staff_id': '',
									'store_id': store_id.toString(),
									'terminal_id': '',
                                };
								rpc.query({
					                model: 'pos.order',
					                method: 'make_signature_api',
					                args: [private_key, JSON.stringify(body)],
					            }).then(function (signature) {
					                var request = new XMLHttpRequest();
	                                request.open('POST', validate_method[0].api_url);
	//								request.setRequestHeader('Content-Type', 'application/json');
	//                                request.setRequestHeader('Access-Control-Allow-Headers', '*');
//									var signature = sign.sign(JSON.stringify(body), CryptoJS.SHA256, "sha256");
									request.setRequestHeader('Signature', signature);
	                                request.onreadystatechange = function () {
	                                    if (this.readyState === 4) {
	                                        var res;
	                                        try {
	                                            res = JSON.parse(this.responseText);
	//											console.log(res)
	                                        } catch(err) {
												if(this.responseText == ""){
													return self.gui.show_popup('alert',{
										                'title': 'Cảnh báo',
										                'body':  'Kết nối API thất bại',
										            });
												}
	                                            var lines = this.responseText.split('\n');
	                                            var json_array = '';
	                                            $.each(lines, function(item, vals){
	                                                if (vals.indexOf('email') >= 0){
	                                                    return
	                                                }
	                                                var text = vals;
	                                                if (vals.indexOf('//') >= 0){
	                                                    var text = vals.split('//')[0];
	                                                }
	                                                json_array += text;
	                                            })
	                                            res = JSON.parse(json_array);
	                                        }
											if(res.length==1){
												res = res[0];
											}
											var order = self.pos.get_order();
											//log response
											var data = {'giftcode_type':giftcode_api[0].type,
													'type':'validate',
													'order_name':order.name,
													'request_string':signature + JSON.stringify(body),
													'response_string':JSON.stringify(res)}
											rpc.query({
								                model: 'giftcode.api.response',
								                method: 'create',
								                args: [data],
								            })
	                                        if (res.done != 1){
	                                            return self.gui.show_popup('error',{'title': _t('Thanh toán không thành công'), 'body':_t(res.data.msg)});
	                                        } else{
	//                                            var order = self.pos.get_order();
	                                            var amount2paid =  order.get_total_with_tax() - order.get_total_paid();
	                                            var amount_paid_by_gifcode = res.data.amount
	                                            if (res.data.amount > amount2paid){
	                                                amount_paid_by_gifcode = amount2paid;
	                                            }
	                                            var cashregister = self.options.cashregister;
	                                            if(order.check_origin_order()){
	                                                order.reset_base_price(true);
	                                                order.remove_current_discount();
	                                                order.unset_promotion_for_coupon();
	                                                order.add_paymentline( cashregister );
	                                                order.selected_paymentline.set_amount(amount_paid_by_gifcode);
	                                                order.selected_paymentline.set_voucher_code(value);
	                                                order.selected_paymentline.use_api_giftcode(true);
	                                                order.use_coupon = true;
	                                                self.gui.current_screen.sort_payment_line()
	                                                self.gui.current_screen.show()
	                                            }else{
													if(order.linked_draft_order_be){
														return self.gui.show_popup('alert',{
											                'title': 'Cảnh báo',
											                'body':  'Đơn hàng đã có khuyến mãi và đã được in label trước hoặc order từ bên ngoài nên không thể thanh toán bằng hình thức này',
											            });
													}
	                                                return self.gui.show_popup('confirm',{
	                                                    'title':  _t('Sử dụng Giftcode trên đơn hàng nguyên giá'),
	                                                    'body':  _t('Nếu xác nhận sử dụng Giftcode trên đơn hàng này, hệ thống sẽ tự động xóa toàn bộ chương trình khuyến mãi trước đó'),
	                                                    'amount': amount_paid_by_gifcode,
	                                                    'cashregister': cashregister,
	                                                    'confirm': function() {
	                                                        order.reset_base_price(true);
	                                                        order.remove_current_discount();
	                                                        order.unset_promotion_for_coupon();
															order.remove_combo_done();
															amount2paid =  order.get_total_with_tax() - order.get_total_paid();
															amount_paid_by_gifcode = res.data.amount
			                                                if (res.data.amount > amount2paid){
			                                                    amount_paid_by_gifcode = amount2paid;
			                                                }
	                                                        order.add_paymentline( this.options.cashregister );
	                                                        order.selected_paymentline.set_amount(amount_paid_by_gifcode);
	                                                        order.selected_paymentline.set_voucher_code(value);
	                                                        order.selected_paymentline.use_api_giftcode(true);
	                                                        order.use_coupon = true;
	                                                        self.gui.current_screen.sort_payment_line()
	                                                        self.gui.current_screen.show()
	                                                    },
	                                                });
	                                            }
	                                        }
	                                    }
	                                };
	                                setTimeout(function() {
	                                    request.send(JSON.stringify(body));
	                                }, 500);
					            },function(error){
									error.event.preventDefault();
					                self.gui.show_popup('error',{
					                    'title': _t('Error: Could not Save Changes'),
					                    'body': _t('Your Internet connection is probably down.'),
					                })
								});
                                break;
                        }
                    }
                }
            }
        },
    });
    gui.define_popup({name:'giftcodeinput', widget: GiftcodeInputPopupWidget});
});