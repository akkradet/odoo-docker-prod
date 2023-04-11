odoo.define('phuclong_pos_giftcode.giftcode', function (require) {
    "use strict";
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var QWeb     = core.qweb;
    var _t = core._t;
    var models = require('point_of_sale.models');
    var rpc = require('web.rpc');
    models.load_fields('pos.payment.method', 'giftcode_api');

    var _super_payment_line = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attr, options) {
            _super_payment_line.initialize.call(this,attr,options);
            this.is_use_api_giftcode = this.is_use_api_giftcode || false;
        },
        init_from_JSON: function(json){
            _super_payment_line.init_from_JSON.apply(this,arguments);
            this.is_use_api_giftcode = json.is_use_api_giftcode || false;
        },
        export_as_JSON: function(){
            var json = _super_payment_line.export_as_JSON.call(this);
            var order = this.pos.get_order();
            json.is_use_api_giftcode = this.is_use_api_giftcode || false;
            return json;
        },
        use_api_giftcode: function(is_use_api){
            this.is_use_api_giftcode = is_use_api;
            this.trigger('change',this);
        },
    });
    screens.PaymentScreenWidget.include({
		click_back: function(){
			var order = this.pos.get_order();
			var lines = order.get_paymentlines();
	        for ( var i = 0; i < lines.length; i++ ) {
	        	if(lines[i].payment_method.use_for=='gift_code'){
					return this.gui.show_popup('alert',{
	                    'title': 'Cảnh báo',
	                    'body':  'Vui lòng xóa thanh toán Giftcode nếu muốn điều chỉnh đơn hàng',
	                });
	        	}
	        }
			this._super();
	    },
        validate_order:function(force_validation){
            var self = this;
			var order = this.pos.get_order();
			if(!order.get_orderlines().length){
				return;
			}
			//Force order from call center
			if(self.pos.config.is_callcenter_pos){
				rpc.query({
		            model: 'pos.order',
		            method: 'get_session_by_warehouse_callcenter',
		            args: [order.warehouse_callcenter_id],
		        }).then(function(result){
					var session_id = result[0];
					var product_lock_ids = result[1];
					order.locked_products = product_lock_ids;
					if (session_id){
						var orderlines = order.get_orderlines();
						for(var i=0; i<orderlines.length; i++){
							if(product_lock_ids.includes(orderlines[i].product.product_tmpl_id)){
								return self.pos.gui.show_popup('alert',{
			                        'title': 'ERROR',
			                        'body':  'Sản phẩm ' + orderlines[i].product.display_name + ' đang nằm trong danh sách khóa món của cửa hàng',
			                    });
							}
						}
						order.session_callcenter_id = session_id;
						order.linked_draft_order_be = order.name;
			            order.state = 'draft';
			            self.pos.push_order(order, {'draft': true});
						order.destroy();
						return;
		        	}else{
		        		return self.pos.gui.show_popup('alert',{
	                        'title': 'ERROR',
	                        'body':  'Không có ca bán hàng hợp lệ tại đang mở bán cửa hàng',
	                    });
		        	}
		        },function(error){
		            error.event.preventDefault();
					self.pos.gui.show_popup('error',{
	                    'title': _t('Error: Could not Save Changes'),
	                    'body': _t('Your Internet connection is probably down.'),
	                });
		        });
				return;
			}
			
			if(!this.order_is_valid(force_validation)){
				return;
			}
//			if(order.has_printed_label_first && order.linked_draft_order_be && !order.pay_draft_order){
			if(order.linked_draft_order_be && !order.pay_draft_order){
				order.pay_draft_order = true;
			}
			var payment_line_exceed = order.check_payment_exceed_amount();
			if (payment_line_exceed){
				return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body':  'Thanh toán từ phương thức ' + payment_line_exceed.payment_method.name + ' đang dư tiền, vui lòng kiểm tra lại',
                });
			}
			
			//check loyalty point neagtive
			if(order.get_spent_points() != 0 && order.get_new_points() < 0){
				return this.pos.chrome.gui.show_popup('alert',{
                    'title': 'Cảnh báo',
                    'body': 'Đơn hàng đang đổi quà nhiều hơn số điểm khả dụng của Khách hàng',
                });
			}
			
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
            
			var lines = this.pos.get_order().get_paymentlines();
			
			if(order.get_total_with_tax() == 0 && lines.length){
				return this.gui.show_popup('alert',{
	                'title': 'Cảnh báo',
	                'body':  'Vui lòng xóa những dòng thanh toán dư',
	            });
			}
			for ( var i = 0; i < lines.length; i++ ) {
	            if (lines[i].amount == 0) {
	            	return this.gui.show_popup('alert',{
		                'title': 'Cảnh báo',
		                'body':  'Vui lòng xóa những dòng thanh toán có giá trị bằng 0',
		            });
	            }
	        }

			if(!self.pos.config.is_callcenter_pos && order.order_in_call_center){
				if(!order.get_note_label()){
					self.chrome.screens.products.numpad.set_label_order();
					return;
	        	}
			}
            
            var code = [];
            var api_code = [];
			var api_code_amount = 0;
			var api_code_array = [];
            var employee_payment = [];
			var partner_payment = [];
            var payment_has_employee_id = [];
			var payment_has_partner_id = [];
            var payment_line = order.paymentlines.models;
    		for(var i in payment_line){
    			//employee payment
    			if(payment_line[i].payment_method.use_for=='on_account_emp' && payment_line[i].amount > 0 
    			 && payment_line[i].employee_id && payment_line[i].max_on_account_amount > 0){
    				employee_payment.push([payment_line[i].employee_id, payment_line[i].amount]);
    				payment_has_employee_id.push(payment_line[i]);

					var on_acc_info = payment_line[i].employee_info + ' - ' + order.format_value(payment_line[i].max_on_account_amount-payment_line[i].amount);
                    payment_line[i].set_on_account_info(on_acc_info);
    			}
				//partner payment
    			if(payment_line[i].payment_method.use_for=='on_account_customer' && payment_line[i].amount > 0 
    			 && payment_line[i].partner_id && payment_line[i].max_on_account_amount > 0){
    				partner_payment.push([payment_line[i].partner_id, payment_line[i].amount]);
    				payment_has_partner_id.push(payment_line[i]);

					var on_acc_info = payment_line[i].partner_info + ' - ' + order.format_value(payment_line[i].max_on_account_amount-payment_line[i].amount);
                    payment_line[i].set_on_account_info(on_acc_info);
    			}
    			//voucher_code
    			if(payment_line[i].voucher_code){
                    if (payment_line[i].is_use_api_giftcode){
                        api_code.push(payment_line[i]);
						api_code_array.push(payment_line[i].voucher_code)
						api_code_amount += payment_line[i].amount;
                    } else{
                        code.push([payment_line[i].voucher_code, 1]);
                    }
    			}
    		}
    		
    		var orderlines = order.get_orderlines();

			//update cashless
			var cashless_lines = orderlines.filter(function(l){
				return l.product.is_cashless && l.cashless_code;
			});
			var cashless_info = [];
			_.each(cashless_lines, function(line){
				cashless_info.push([line.cashless_code, line.product.effective_day]);
			})
			
			//update product coupon code
			var product_coupon_lines = orderlines.filter(function(l){
				return l.product.update_coupon_expiration && l.product_coupon_code;
			});
			var product_coupon_info = [];
			_.each(product_coupon_lines, function(line){
				product_coupon_info.push([line.product_coupon_code, line.product.effective_day]);
			})
			//update product apply coupon code
			var apply_product_coupon_lines = orderlines.filter(function(l){
				return l.cup_type == 'themos' && l.product_coupon_code;
			});
			var apply_product_coupon_info = [];
			_.each(apply_product_coupon_lines, function(line){
				var exist_line = apply_product_coupon_info.filter(function(x){
					return x[0] == line.product_coupon_code;
				})
				if(exist_line.length){
					exist_line[0][1] += line.quantity;
				}else{
					apply_product_coupon_info.push([line.product_coupon_code, line.quantity]);
				}
			})

    		var partner_id = false;
    		var partner = this.pos.get_client() || false;
    		if(partner){
    			partner_id = partner.id;
    		}
    		
//    		var code = order.coupon_code;
    		var coupon_code_backend = []
    		if(order.coupon_code_array.length){
    			//unset current_coupon_code if coupon_code_array doesn't containt it
    			if(order.current_coupon_code && !order.coupon_code_array.includes(order.current_coupon_code)){
    				order.set_current_coupon_info('', 0, false);
    			}
    			for(var c in order.coupon_code_array){
    				var used_count = 0;
    	    		if(order.current_coupon_code && order.coupon_code_array[c] == order.current_coupon_code && order.current_coupon_limit && order.current_coupon_promotion){
    	                for(var i = 0; i < orderlines.length; i++){
    	                	if(orderlines[i].promotion_id && orderlines[i].promotion_line_id == order.current_coupon_promotion){
    	                		used_count += orderlines[i].quantity;
    	        			}
    	                }
    	    		}else{
    	    			coupon_code_backend.push(order.coupon_code_array[c]);
    	    			used_count = 1
    	    		}
    				code.push([order.coupon_code_array[c], used_count]);
    			}
    		}
    		if(coupon_code_backend.length){
    			order.coupon_code_list = coupon_code_backend.join(', ')
    		}else{
    			order.coupon_code_list = '';
    		}
    		var warehouse_id = self.pos.config.warehouse_id;
            
            //write reward code
			var reward_orderline = order.orderlines.models.filter(function(item){
                return item.product.default_code == 'reward_code';
            })
            if (reward_orderline.length && !order.done_reward_code){
                rpc.query({
                    model: 'pos.order',
                    method: 'update_set_done_reward_code',
                    args: [reward_orderline[0].quantity, order.name, reward_orderline[0].promotion_line_id],
                }).then(function(result_from_server){
                    if(result_from_server){
						order.reward_code = result_from_server[0];
                        order.done_reward_code = result_from_server[0];
						order.reward_description = result_from_server[1];
						order.reward_link = result_from_server[2];
                        self.validate_order(force_validation);
                    }else{
//                        order.reward_code = false;
                        order.done_reward_code = false;
                        return self.gui.show_popup('error',{
                            'title': _t('Error: Could not Save Changes'),
                            'body': _t('Mã dự thưởng không hợp lệ hoặc đã được sử dụng'),
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            }else if (cashless_info.length && !order.done_cashless_code){
                rpc.query({
                    model: 'pos.order',
                    method: 'update_cashless_code',
                    args: [cashless_info, order.name],
                }).then(function(result_from_server){
                    if(result_from_server.length){
                        order.done_cashless_code = true;
						_.each(result_from_server, function(l){
							var card_code = self.pos.db.card_code_by_barcode[l[0]] || false;
							if(card_code){
								card_code.date_expired = l[1]
							}
						})
                        self.validate_order(force_validation);
                    }else{
                        order.done_cashless_code = false;
                        return self.gui.show_popup('error',{
                            'title': _t('Error: Could not Save Changes'),
                            'body': 'Mã thẻ Cashless khách hàng không hợp lệ hoặc đã được sử dụng',
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            }else if (product_coupon_info.length && !order.done_product_coupon_code){
                rpc.query({
                    model: 'pos.order',
                    method: 'update_done_product_coupon_code',
                    args: [product_coupon_info, order.name],
                }).then(function(result_from_server){
                    if(result_from_server){
                        order.done_product_coupon_code = true;
                        self.validate_order(force_validation);
                    }else{
                        order.done_product_coupon_code = false;
                        return self.gui.show_popup('error',{
                            'title': _t('Error: Could not Save Changes'),
                            'body': 'Mã Coupon không hợp lệ hoặc đã được sử dụng',
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            }else if (apply_product_coupon_info.length && !order.done_apply_product_coupon_code){
                rpc.query({
                    model: 'sale.promo.header',
                    method: 'update_set_done_coupon',
                    args: [apply_product_coupon_info, order.name, partner_id, warehouse_id[0]],
                }).then(function(result_from_server){
                    if(result_from_server == true){
                        order.done_apply_product_coupon_code = true;
                        self.validate_order(force_validation);
                    }else{
                        order.done_apply_product_coupon_code = false;
                        return self.gui.show_popup('error',{
                            'title': _t('Error: Could not Save Changes'),
                            'body': 'Mã Coupon không hợp lệ hoặc đã được sử dụng: ' + result_from_server,
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            }else if(employee_payment.length){
            	rpc.query({
                    model: 'hr.employee',
                    method: 'update_employee_on_account_amount',
                    args: [employee_payment, order.name],
                }).then(function(result_from_server){
                    if(result_from_server == true){
                        for(var pay in payment_has_employee_id){
                        	payment_has_employee_id[pay].set_max_on_account_amount(0);
                        }
                        self.validate_order(force_validation);
                    }else{
                    	return self.gui.show_popup('alert',{
                            'title': 'Cảnh báo',
                            'body':  'Số tiền thanh toán vượt quá số tiền còn lại trong tài khoản: ' + self.format_currency(result_from_server) +  '. Vui lòng kiểm tra lại',
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            	
            }else if(partner_payment.length){
            	rpc.query({
                    model: 'res.partner',
                    method: 'update_partner_on_account_amount',
                    args: [partner_payment, order.name],
                }).then(function(result_from_server){
                    if(result_from_server == true){
                        for(var pay in payment_has_partner_id){
                        	payment_has_partner_id[pay].set_max_on_account_amount(0);
                        }
						//update partner cache
						_.each(partner_payment, function(p){
							var partner = self.pos.db.get_partner_by_id(p[0]);
							partner.wallet_on_account = partner.wallet_on_account - p[1];
						})
                        self.validate_order(force_validation);
                    }else{
                    	return self.gui.show_popup('alert',{
                            'title': 'Cảnh báo',
                            'body':  'Số tiền thanh toán vượt quá số tiền còn lại trong tài khoản: ' + self.format_currency(result_from_server) +  '. Vui lòng kiểm tra lại',
                        });
                    }
                },function(error){
					error.event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                });
            	
            }else if (order.use_coupon && code != undefined && code.length > 0){
    			rpc.query({
                    model: 'sale.promo.header',
                    method: 'update_set_done_coupon',
                    args: [code, order.name, partner_id, warehouse_id[0]],
                })
    			.then(function(result_from_server){
    				if(order.use_coupon){
    					if(result_from_server == true){
    						order.set_coupon_code('');
    						order.use_coupon = false;
    						order.trigger('change',order);
    						self.validate_order(force_validation);
    					}else{
    						self.gui.show_popup('error',{
    			                'title': _t('Error: Could not Save Changes'),
    			                'body': _t('Coupon/Voucher không hợp lệ hoặc đã được sử dụng: ' + result_from_server),
    			            });
    					}
    				}
    			},function(error){
					error.event.preventDefault();
    				self.gui.show_popup('error',{
    	                'title': _t('Error: Could not Save Changes'),
    	                'body': _t('Your Internet connection is probably down.'),
    	            });
                });
            }else if (api_code != undefined && api_code.length > 0 && order.done_api_payment_code < api_code.length){
                // Call api to activate giftcodes
                var code_string = api_code_array.join(',')
				var list_payment_api = api_code;
				api_code = api_code[0];
                async function activateApi(api_code) {
                    // notice that we can await a function
                    // that returns a promise
                    var api_config = self.pos.db.api_configs.filter(function(item){
                        return item.id == api_code.payment_method.giftcode_api[0];
                    })[0]
                    var validate_method = self.pos.db.api_config_methods.filter(function(item){
                        return item.api_config_id[0] == api_config.id && item.type == 'activate'
                    })[0]
					var store_id = api_config.brand_id;
					if(api_config.store_mapping_type == 'one2one'){
						var store_config = self.pos.db.api_config_stores.filter(function(item){
	                        return item.store_conf_id && item.store_conf_id[0] == api_config.id && item.store_id[0] == warehouse_id[0];
	                    })
						if(store_config.length){
							store_id = store_config[0].gifcode_store_id;
						}
					}
					var private_key = '-----BEGIN RSA PRIVATE KEY-----\n'+
									  api_config.sec_key +
									  '\n-----END RSA PRIVATE KEY-----';
//					var sign = new JSEncrypt();
//					sign.setPrivateKey(private_key);
                    switch(api_config.type){
						case "giftpop":
							var list_voucher = [];
							_.each(list_payment_api, function(payment){
								list_voucher.push({'pinNo':payment.voucher_code,
												   'usePrice':payment.api_voucher_amount})
							})
                            var body = {
								'referenceNumber': order.name,
								'authKey': api_config.access_key,
                                'brandCode': api_config.branch_code,
								'storeCode': store_id.toString(),
								'pinNoList': list_voucher,
                            };
							
							rpc.query({
				                model: 'pos.order',
				                method: 'make_signature_api',
				                args: [private_key, JSON.stringify(body)],
				            }).then(function (signature) {
								var request = new XMLHttpRequest();
	                            request.open('POST', validate_method.api_url);
	                            request.setRequestHeader('Content-Type', 'application/json');
//								var signature = sign.sign(JSON.stringify(body), CryptoJS.SHA256, "sha256");
								request.setRequestHeader('Signature', signature);
	                            request.onreadystatechange = function () {
	                                if (this.readyState === 4) {
	                                    var res;
	                                    try {
	                                        res = JSON.parse(this.responseText);
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
	//									var order = self.pos.get_order();
										//log response
										var data = {'giftcode_type':api_config.type,
												'type':'activate',
												'order_name':order.name,
												'request_string':JSON.stringify(body),
												'response_string':JSON.stringify(res)}
										rpc.query({
							                model: 'giftcode.api.response',
							                method: 'create',
							                args: [data],
							            })
										
										//9051 -> has payment sucess
										if ((res.resCodeTrans != '0000' && res.resCodeTrans != '9051') || !res.pinInfo || !res.pinInfo.length){
											var error = [res.messageTrans];
											if(res.pinInfo && res.pinInfo.length){
												_.each(res.pinInfo, function(l){
													error.push(l.pinNo + ' :' + l.message);
												})
											}
											return self.gui.show_popup('alert',{
								                'title': 'Thanh toán không thành công',
								                'body':  error,
								            });
	                                    }else{
	//										_.each(res.pinInfo, function(result){
	//											if (result.pinStatus != 'R' && result.pinStatus != 'U'){
	//		                                        return self.gui.show_popup('alert',{
	//									                'title': 'Thanh toán không thành công. Mã voucher :' + result.pinNo,
	//									                'body': result.message,
	//									            });
	//		                                    }else{
	//												order.done_api_payment_code += 1;
	//											}
	//										})
											order.done_api_payment_code = res.pinInfo.length;
											if(order.done_api_payment_code < api_code_array.length){
												return self.gui.show_popup('error',{'title': 'Áp dụng Giftcode không thành công, vui lòng thử lại'});
											}                                  
		                                    if (self.order_is_valid(force_validation)){
		//                                        order.done_api_payment_code = true;
		                                        order.trigger('change',order);
		                                        self.validate_order(force_validation);
		                                    }
										}
	                                }
	                            };
	                            request.send(JSON.stringify(body));
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
								'amount': api_code.amount,
								'app_id': api_config.agent_site,
                                'app_secret': api_config.access_key,
								'bill_id': order.name,
                                'code': code_string,
								'staff_id': '',
								'store_id': store_id.toString(),
								'terminal_id': '',
								'time': (new Date).format('d-m-Y H:i:s'),
                            };
							
							rpc.query({
				                model: 'pos.order',
				                method: 'make_signature_api',
				                args: [private_key, JSON.stringify(body)],
				            }).then(function (signature) {
								var request = new XMLHttpRequest();
	                            request.open('POST', validate_method.api_url);
	//                            request.setRequestHeader('Content-Type', 'application/json');
//								var signature = sign.sign(JSON.stringify(body), CryptoJS.SHA256, "sha256");
								request.setRequestHeader('Signature', signature);
	                            request.onreadystatechange = function () {
	                                if (this.readyState === 4) {
	                                    var res;
	                                    try {
	                                        res = JSON.parse(this.responseText);
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
	//									var order = self.pos.get_order();
										//log response
										var data = {'giftcode_type':api_config.type,
												'type':'activate',
												'order_name':order.name,
												'request_string':JSON.stringify(body),
												'response_string':JSON.stringify(res)}
										rpc.query({
							                model: 'giftcode.api.response',
							                method: 'create',
							                args: [data],
							            })
										
										_.each(res, function(result){
											if (result.done != 1){
		                                        return self.gui.show_popup('error',{'title': _t('Áp dụng Giftcode không thành công'), 'body':_t(result.msg)});
		                                    }else{
												order.done_api_payment_code += 1;
											}
										})
										
										if(order.done_api_payment_code < api_code_array.length){
											return self.gui.show_popup('error',{'title': 'Áp dụng Giftcode không thành công, vui lòng thử lại'});
										}                                  
	                                    if (self.order_is_valid(force_validation)){
	//                                        order.done_api_payment_code = true;
	                                        order.trigger('change',order);
	                                        self.validate_order(force_validation);
	                                    }
	                                }
	                            };
	                            request.send(JSON.stringify(body));
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
                async function processActivateGiftcode(array) {
//                    array.forEach(async (item) => {
//                        await activateApi(item);
//                    })
					 await activateApi(array);
                }
                processActivateGiftcode(api_code);
    		}else{
            	if (this.order_is_valid(force_validation)) {
                    this.finalize_validation();
                }
            }
        },
        render_paymentmethods: function() {
            var self = this;
            var methods = $(QWeb.render('PaymentScreen-Paymentmethods', { widget:this }));
                methods.on('click','.paymentmethod',function(){
                    self.click_paymentmethods($(this).data('id'));
                });
                methods.on('click','.giftcode-method',function(){
                    self.click_giftcode_paymentmethods();
                });
            return methods;
        },
        click_paymentmethods: function(id) {
            var self = this;
			var order = this.pos.get_order();
			var lines = order.get_paymentlines();
			if(order.is_paid()){
				return this.pos.chrome.gui.show_popup('alert',{
	                'title': 'Cảnh báo',
	                'body':  'Đơn hàng đã thanh toán đủ tiền',
	            });
			}
            var cashregister = this.pos.payment_methods_by_id[id];
			if(cashregister.use_for == "cash" && !cashregister.use_for_voucher){
				for(var i=0; i< lines.length; i++){
					if(lines[i].payment_method.id == cashregister.id){
						return self.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã có dòng thanh toán tiền mặt',
			            });
					}
				}
				this._super(id);
			}else if(cashregister.use_for == "gift_code"){
                if (!cashregister.giftcode_api){
                    return this.gui.show_popup('error',_t('Phương thức thanh toán Giftcode API chưa sẵn sàng.'));
                }
				for(var i=0; i< lines.length; i++){
					if(lines[i].payment_method.use_for == 'gift_code' && lines[i].payment_method.id != cashregister.id){
						return self.gui.show_popup('alert',{
			                'title': 'Cảnh báo',
			                'body':  'Đơn hàng đã thanh toán bằng hình thức Giftcode khác',
			            });
					}
				}
                return self.gui.show_popup('giftcodeinput',{
                    title: _t('Nhập mã ' + cashregister.name + ' để thanh toán'),
                    cashregister:cashregister,
                });
            }else {
                this._super(id);
            }
        },
        click_giftcode_paymentmethods: function() {
            var self = this;
            var gift_code_journal = [];
            var giftcode_method = this.pos.payment_methods.filter(function(item){return item.use_for == 'gift_code'});
            for ( var i = 0; i < giftcode_method.length; i++ ) {
                gift_code_journal.push({
                    label : giftcode_method[i].name,
                    item: giftcode_method[i].id,
                });
            }
            if(!gift_code_journal.length){
                this.gui.show_popup('error',_t('Phương thức thanh toán Giftcode chưa được thiết lập'));
            }else if(gift_code_journal.length == 1){
                self.click_paymentmethods(gift_code_journal[0].item);
            }else{
                this.gui.show_popup('selection',{
                    'title': _t('Chọn phương thức thanh toán'),
                    'list': gift_code_journal,
                    'confirm':function(journal_id){
                        self.click_paymentmethods(journal_id);
                    },
                });
            }
        },
		sort_payment_line(){
	    	var self = this;
	    	var order = this.pos.get_order();
	    	var lines = this.pos.get_order().get_paymentlines();
	    	if(lines.length<2){
	            order.selected_paymentline.set_selected(false);
	            order.selected_paymentline = undefined;
	            self.reset_input();
	            self.render_paymentlines();
	    		return true;
	    	}
	    	var temp_line = false;
	        for ( var i = 0; i < lines.length-1; i++ ) {
	        	for ( var j=i+1; j < lines.length; j++ ) {
		            if (lines[j].payment_method.use_for_voucher == true){
		            	if (lines[i].payment_method.use_for_voucher == false){
		            		temp_line = lines[j];
		            		lines[j] = lines[i];
		            		lines[i] = temp_line;
		            	}
		            }
	        	}
	        	var temp_line = lines[lines.length-1];
	        }
	        this.pos.get_order().select_paymentline(temp_line);
	        if(temp_line.payment_method.use_for_voucher == true || temp_line.payment_method.use_for == "gift_code"){
	        	order.selected_paymentline.set_selected(false);
	            order.selected_paymentline = undefined;
	        }
	        this.reset_input();
	        this.render_paymentlines();
	        return true;
	    },
    });
});