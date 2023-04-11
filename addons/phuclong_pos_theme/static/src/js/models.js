odoo.define('phuclong_pos_theme.pos_models', function (require) {
	"use strict";
	var core = require('web.core');
	var models = require('point_of_sale.models');
	var screens = require('point_of_sale.screens');
	var utils = require('web.utils');
	var round_pr = utils.round_precision;
	var rpc = require('web.rpc');
	var session = require('web.session');
	var time = require('web.time');
	var utils = require('web.utils');
	var _t = core._t;

	models.load_fields('product.product', ['suitable_topping_ids', 'fnb_type', 'size_id', 'parent_code',
		'custom_material_ids', 'short_name', 'eng_name', 'name', 'pos_sequence',
		'is_cashless', 'effective_day', 'update_coupon_expiration']);
	models.load_fields('pos.category', 'allow_show_original_price');
	models.load_fields('pos.payment.method', ['use_for', 'logo', 'journal_type', 'sequence']);

	models.load_models([
		{
			model: 'pos.sale.type',
			fields: [
				'name',
				'description',
				'logo',
				'use_for_call_center',
				'allow_print_label_first',
				'show_original_subtotal'
			],
			domain: function (self) {
				return [
					['active', '=', true],
					'|',
					['id', 'in', self.config.sale_type_ids],
					['id', '=', self.config.sale_type_default_id[0]]
				];
			},
			loaded: function (self, sale_type_ids) {
				self.db.add_sale_types(sale_type_ids);
				self.db.check_dollar_pos(self.config.is_dollar_pos);
			},
		}, {
			model: 'product.size',
			fields: ['name', 'sequence'],
			loaded: function (self, size_ids) {
				self.size_ids = size_ids || [];
				self.db.add_size_ids(size_ids);
			},
		}, {
			model: 'pos.payment.method.visa',
			fields: ['code', 'payment_method_id'],
			loaded: function (self, payment_method_visa) {
				self.payment_method_visa = payment_method_visa || [];
			},
		}, {
			model: 'product.cup.default',
			fields: [
				'product_id',
				'sale_type_id',
				'cup_type_load_pos'
			],
			domain: function (self) {
				return [
					['cup_type_load_pos', '!=', 'none']
				];
			},
			loaded: function (self, default_cup_ids) {
				self.db.add_default_cups(default_cup_ids);
			},
		}, {
			model: 'product.material',
			fields: [
				'product_custom_id',
				'name',
				'option_unavailable_dom',
			],
			loaded: function (self, material_ids) {
				self.db.add_material_ids(material_ids);
			},
		}, {
			model: 'res.currency',
			fields: [
				'name',
				'symbol',
				'position',
				'rounding',
				'rate'
			],
			loaded: function (self, currencies) {
				self.currencies = currencies;
				for (var i in currencies) {
					if (currencies[i].id == self.config.currency_id[0]) {
						self.currency = currencies[i];
					} else if (currencies[i].id == self.company.currency_id[0]) {
						self.company_currency = currencies[i];
					}
				}
				if (self.currency.rounding > 0 && self.currency.rounding < 1) {
					self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
				} else {
					self.currency.decimals = 0;
				}

			},
		}
		//		,{
		//        	model: 'stock.warehouse',
		//            fields: ['id','code', 'display_name'],
		//            loaded: function(self,warehouse_ids){
		//            	self.warehouse_ids = warehouse_ids || [];
		//				self.db.add_warehouse_ids(warehouse_ids);
		//            },
		//        },
	]);

	var posmodel_super = models.PosModel.prototype;
	models.PosModel = models.PosModel.extend({
		initialize: function (session, attributes) {
			this.callcenter_count = 0;
			var result = posmodel_super.initialize.call(this, session, attributes);
			return result;
		},
		_save_to_server: function (orders, options) {
			if (!orders || !orders.length) {
				return Promise.resolve([]);
			}

			options = options || {};

			var self = this;
			var timeout = typeof options.timeout === 'number' ? options.timeout : 15000 * orders.length;

			// Keep the order ids that are about to be sent to the
			// backend. In between create_from_ui and the success callback
			// new orders may have been added to it.
			var order_ids_to_sync = _.pluck(orders, 'id');

			// we try to send the order. shadow prevents a spinner if it takes too long. (unless we are sending an invoice,
			// then we want to notify the user that we are waiting on something )
			var args = [_.map(orders, function (order) {
				order.to_invoice = options.to_invoice || false;
				return order;
			})];
			args.push(options.draft || false);
			return rpc.query({
				model: 'pos.order',
				method: 'create_from_ui',
				args: args,
				kwargs: { context: session.user_context },
			}, {
				timeout: timeout,
				shadow: !options.to_invoice
			})
				.then(function (server_ids) {
					_.each(order_ids_to_sync, function (order_id) {
						self.db.remove_order(order_id);
					});
					self.set('failed', false);
					return server_ids;
				}).catch(function (reason) {
					var error = reason.message;
					if (error.code === 200) {    // Business Logic Error, not a connection problem
						//if warning do not need to display traceback!!
						if (error.data.exception_type == 'warning') {
							delete error.data.debug;
						}

						// Hide error if already shown before ...
						if ((!self.get('failed') || options.show_error) && !options.to_invoice) {
							self.gui.show_popup('error-traceback', {
								'title': error.data.message,
								'body': error.data.debug
							});
						}
						self.set('failed', error);
					}
					console.warn('Failed to send orders:', orders);
					//	                self.gui.show_sync_error_popup();
					throw reason;
				});
		},
		load_server_data: function () {
			var self = this;
			var res_partner_index = _.findIndex(this.models, function (model) {
				return model.model === "res.partner";
			});

			var partner_model = this.models[res_partner_index];
			var partner_ignore_fields = ['city', 'country_id', 'phone', 'zip', 'barcode', 'property_account_position_id', 'property_product_pricelist', 'ref', 'category_id'];
			partner_model.fields = partner_model.fields.filter(function (l) {
				return !partner_ignore_fields.includes(l);
			});
			return posmodel_super.load_server_data.apply(this, arguments)
		},
		after_load_server_data: function () {
			var self = this;
			//set up qz
			if (!qz.websocket.isActive()) {
				if (self.config.use_replacement_printer && self.config.printer_ip) {
					qz.websocket.connect({ host: self.config.printer_ip }).then(function () {
						self.first_print();
					});
				} else {
					qz.websocket.connect().then(function () {
						self.first_print();
					});
				}
			} else {
				self.first_print();
			}
			self.payment_methods = _.sortBy(self.payment_methods, function (line) { return !(line.use_for == 'cash') && line.sequence; });
			self.giftcode_method = false;
			var giftcode_method = self.payment_methods.filter(function (item) { return item.use_for == 'gift_code' });
			if (giftcode_method.length) {
				self.giftcode_method = giftcode_method[0];
			}
			return posmodel_super.after_load_server_data.apply(this, arguments).then(function () {
				var session_id = self.pos_session.id;
				rpc.query({
					model: 'pos.order',
					method: 'check_draft_order',
					args: [session_id],
				}).then(function (draft_order_count) {
					if (draft_order_count) {
						self.draft_order_count = draft_order_count;
						self.callcenter_count = self.draft_order_count;
						self.reset_history_order_count();
					} else {
						self.draft_order_count = 0;
					}
				})
			});
		},
		first_print: function () {
			return;
			//			qz.printers.find('POS Order').then(function(printer) {
			//                var config = qz.configs.create(printer, []);
			//                var data = [{
			//                    type: 'pixel',
			//					format: 'html',
			//					flavor: 'plain',
			//                    data: ''
			//                }];  // Raw ZPL
			//                qz.print(config, data);
			//            })
		},
		check_method_has_payment: function (payment_method_id) {
			var payment_lines = this.get_order().get_paymentlines();
			var lines_by_method = payment_lines.filter(function (l) {
				return l.payment_method.id == payment_method_id;
			})
			if (lines_by_method.length) {
				return true;
			}
			return false;
		},
		format_pr: function (value, precision = false) {
			if (!value) {
				value = 0;
			}
			var decimals = precision > 0 ? Math.max(0, Math.ceil(Math.log(1.0 / precision) / Math.log(10))) : 0;
			return value.toFixed(decimals);
		},

		//call center notify
		receiver_message: function (message) {
			var error = false;
			if (message && Array.isArray(message)) {
				if (message[0] == 'callcenter') {
					try {
						this.draft_order_count = message[1] || 0;
						if ($('.button.history-order')) {
							this.callcenter_count = this.draft_order_count;
							this.reset_history_order_count();
							if (this.draft_order_count) {
								$('.button.history-order').addClass('history-highlight');
							} else {
								$('.button.history-order').removeClass('history-highlight');
							}
						}
					} catch (err) {
						console.log(error);
					}
				}
			}
			posmodel_super.receiver_message.apply(this, message);
		},
		delete_current_order: function () {
			var self = this;
			var order = this.get_order();
			posmodel_super.delete_current_order.call(this);
			if (order.order_in_call_center) {
				this.callcenter_count -= 1;
				this.reset_history_order_count();
			}
			if (order.order_in_app) {
				if (self.mobile_order_list && self.mobile_order_list.includes(order.name)) {
					self.mobile_order_list = self.mobile_order_list.filter(function (l) {
						return l != order.name;
					})
				}
				this.reset_mobile_order_status();
			}
		},
		reset_history_order_count: function () {
			$('.button.history-order').attr('data-callcenter-count', this.callcenter_count);
			if (this.callcenter_count) {
				$('.button.history-order .badge').removeClass('hidden').text(this.callcenter_count);
			} else {
				$('.button.history-order .badge').addClass('hidden');
			}
		}

	});

	var _super_order = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function () {
			_super_order.initialize.apply(this, arguments);
			this.sale_type_id = this.sale_type_id || this.get_sale_type_default()[0];
			this.sale_type_name = this.sale_type_name || this.get_sale_type_default()[1]
			if (this.pos.config.is_callcenter_pos) {
				this.sale_type_name = 'Chọn cửa hàng';
			}
			this.number_of_printed_bill = this.number_of_printed_bill || 1;
			this.date_first_order = this.date_first_order || false;
			this.date_last_order = this.date_last_order || false;
			this.reward_code = this.reward_code || false;
			this.done_reward_code = this.done_reward_code || false;
			this.done_cashless_code = this.done_cashless_code || false;
			this.done_product_coupon_code = this.done_product_coupon_code || false;
			this.done_apply_product_coupon_code = this.done_apply_product_coupon_code || false;
			this.done_api_payment_code = this.done_api_payment_code || 0;
			this.reward_description = this.reward_description || '';
			this.reward_link = this.reward_link || '';
			this.has_printed_label_first = this.has_printed_label_first || false;
			this.linked_draft_order_be = this.linked_draft_order_be || '';
			this.order_in_app = this.order_in_app || false;
			this.order_in_call_center = this.pos.config.is_callcenter_pos || false;
			this.warehouse_callcenter_id = this.warehouse_callcenter_id || false;
			this.session_callcenter_id = this.session_callcenter_id || false;
			this.pay_draft_order = this.pay_draft_order || false;
			//invoice info
			this.invoice_name = this.invoice_name || '';
			this.invoice_vat = this.invoice_vat || '';
			this.invoice_address = this.invoice_address || '';
			this.invoice_email = this.invoice_email || '';
			this.invoice_contact = this.invoice_contact || '';
			this.invoice_note = this.invoice_note || '';
			this.invoice_request = this.invoice_request || false;
			this.locked_products = this.locked_products || [];
		},
		export_as_JSON: function () {
			var json = _super_order.export_as_JSON.call(this);
			json.sale_type_id = this.sale_type_id;
			json.sale_type_name = this.sale_type_name;
			json.number_of_printed_bill = this.number_of_printed_bill || 1;
			json.date_first_order = this.date_first_order || false;
			json.date_last_order = this.validation_date;
			json.reward_code = this.reward_code || false;
			json.done_reward_code = this.done_reward_code || false;
			json.done_cashless_code = this.done_cashless_code || false;
			json.done_product_coupon_code = this.done_product_coupon_code || false;
			json.done_apply_product_coupon_code = this.done_apply_product_coupon_code || false;
			json.done_api_payment_code = this.done_api_payment_code || 0;
			json.reward_description = this.reward_description || false;
			json.reward_link = this.reward_link || false;
			json.has_printed_label_first = this.has_printed_label_first || false;
			json.linked_draft_order_be = this.linked_draft_order_be || '';
			json.order_in_app = this.order_in_app || false;
			json.order_in_call_center = this.order_in_call_center || false;
			json.warehouse_callcenter_id = this.warehouse_callcenter_id || false;
			json.session_callcenter_id = this.session_callcenter_id || false;
			json.pay_draft_order = this.pay_draft_order || false;
			//invoice info
			json.invoice_name = this.invoice_name || '';
			json.invoice_vat = this.invoice_vat || '';
			json.invoice_address = this.invoice_address || '';
			json.invoice_email = this.invoice_email || '';
			json.invoice_contact = this.invoice_contact || '';
			json.invoice_note = this.invoice_note || '';
			json.invoice_request = this.invoice_request || false;
			return json;
		},
		init_from_JSON: function (json) {
			_super_order.init_from_JSON.apply(this, arguments);
			this.sale_type_id = json.sale_type_id;
			this.sale_type_name = json.sale_type_name;
			this.number_of_printed_bill = json.number_of_printed_bill || 1;
			this.date_first_order = json.date_first_order || false;
			this.reward_code = json.reward_code || false;
			this.done_reward_code = json.done_reward_code || false;
			this.done_cashless_code = json.done_cashless_code || false;
			this.done_product_coupon_code = json.done_product_coupon_code || false;
			this.done_apply_product_coupon_code = json.done_apply_product_coupon_code || false;
			this.done_api_payment_code = json.done_api_payment_code || 0;
			this.reward_description = json.reward_description || '';
			this.reward_link = json.reward_link || ''
			this.has_printed_label_first = json.has_printed_label_first || false;
			this.linked_draft_order_be = json.linked_draft_order_be || '';
			this.order_in_app = json.order_in_app || false;
			this.order_in_call_center = json.order_in_call_center || false;
			this.warehouse_callcenter_id = json.warehouse_callcenter_id || false;
			this.session_callcenter_id = json.session_callcenter_id || false;
			this.pay_draft_order = json.pay_draft_order || false;
			//invoice info
			this.invoice_name = json.invoice_name || '';
			this.invoice_vat = json.invoice_vat || '';
			this.invoice_address = json.invoice_address || '';
			this.invoice_email = json.invoice_email || '';
			this.invoice_contact = json.invoice_contact || '';
			this.invoice_note = json.invoice_note || '';
			this.invoice_request = json.invoice_request || false;
		},
		add_product: function (product, options) {
			var line = _super_order.add_product.call(this, product, options);
			if (this.orderlines.length == 1 && this.date_first_order == false) {
				this.date_first_order = new Date();
			}
			return line;
		},
		get_sale_type_default: function () {
			return this.pos.config.sale_type_default_id;
		},
		set_sale_type: function (sale_type) {
			var rerender = false;
			this.sale_type_id = sale_type.id;
			this.sale_type_name = sale_type.name;
			//Vuong: update promotion when change sale type
			this.reset_base_price_no_compute(true);
			this.remove_current_discount();
			var orderlines = this.get_orderlines();
			for (var line in orderlines) {
				var product = orderlines[line].product;
				var quantity = orderlines[line].quantity;
				if (orderlines[line].combo_id) {
					if (!orderlines[line].check_use_price_combo) {
						orderlines[line].set_price(product.list_price);
						this.get_base_price_by_line(product, quantity, orderlines[line], true, rerender);
						this.get_new_price(product, quantity, orderlines[line]);
					}
				} else {
					this.get_new_price(product, orderlines[line].quantity, orderlines[line]);
				}
				//update sale type
				if (product.fnb_type == 'drink') {
					if (orderlines[line].product_coupon_code && orderlines[line].cup_type == 'themos') {
						orderlines[line].remove_discount_line(true);
					} else {
						var cup_type = this.get_default_cup_by_product(product);
						if (cup_type == 'paper_1st') {
							cup_type = 'paper';
						}
						if (cup_type == 'plastic_1st') {
							cup_type = 'plastic';
						}
						orderlines[line].set_cup_type(cup_type);
						orderlines[line].set_cup_type_default(cup_type);
					}
				}
			}
			this.compute_promotion();
			//Thai: Update Surcharge when change sale type:
			this.compute_surcharge_order();
			this.rerender_all_line();
			this.trigger('change', this);
		},
		get_sale_type_by_id: function (sale_type_id) {
			var self = this;
			var sale_type_ids = self.pos.db.sale_type_ids;
			for (var i in sale_type_ids) {
				if (sale_type_ids[i].id == sale_type_id) {
					return sale_type_ids[i];
				}
			}
			return false
		},
		//        get_product_cup_by_size: function(product){
		//        	var self = this;
		//	    	var default_sale_type = this.get_sale_type_default();
		//	    	if(this.sale_type_id && default_sale_type && this.sale_type_id == default_sale_type[0]){
		//	    		return this.pos.db.product_cup_by_size[product.size_id[0]];
		//	    	}else{
		//	    		if(this.sale_type_id){
		//	    			var default_cups = this.pos.db.default_cups_by_product_tmpl[product.product_tmpl_id];
		//	    			for(var cup in default_cups){
		//	    				if(default_cups[cup].sale_type_id[0] == this.sale_type_id){
		//	    					var cup_product = this.pos.db.product_by_tmpl_id[default_cups[cup].cup_id[0]];
		//	    					return [cup_product];
		//	    				}
		//	    			}
		//	    		}
		//	    	}
		//    		return false;
		//	        
		//	    },
		get_default_cup_by_product: function (product) {
			var self = this;
			if (this.sale_type_id) {
				var default_cups = this.pos.db.default_cups_by_product_tmpl[product.product_tmpl_id];
				for (var cup in default_cups) {
					if (default_cups[cup].sale_type_id[0] == this.sale_type_id) {
						var cup_product_type = default_cups[cup].cup_type_load_pos;
						return cup_product_type;
					}
				}
			}
			return false;

		},
		get_orderlines_no_topping: function () {
			var lines_note_topping = this.orderlines.models.filter(function (line) { return !line.is_topping_line }
			);
			return lines_note_topping;
		},
		get_kitchen_product_line: function () {
			var self = this;
			var res = [];
			var order_lines = this.get_orderlines_no_topping();
			var fnb_order_lines = order_lines.filter(function (line) {
				return (line.product.fnb_type == 'food' || line.product.fnb_type == 'packaged_product') && !line.is_topping_line;
			})
			_.each(fnb_order_lines, function (item) {
				var line = { ...item };
				if (line.note.length > 0) {
					// thêm sản phẩm có ghi chú
					res.push(line)
				} else {
					// cập nhật số lượng sản phẩm không có ghi chú
					var added_line = res.filter(function (r) {
						return r.product.id == line.product.id && r.note.length == 0
					})
					if (added_line.length > 0) {
						_.each(res, function (r) {
							if (r.product.id == line.product.id && r.note.length == 0) {
								r.quantity += line.quantity;
							}
						})
					} else {
						res.push(line)
					}
				}
			})
			return res;
		},
		get_orderlines_groupby_combo: function (return_order = false) {
			var self = this;
			var res = [];
			var added_line = [];
			var order_lines = this.get_orderlines_no_topping();
			if (return_order) {
				order_lines = self.order_to_return[0].orderlines.filter(function (item) { return item.is_topping_line == false });
			}
			var sequence = 0;
			_.each(_.sortBy(order_lines, 'id', 'asc'), function (item) {
				if (!item.is_done_combo) {
					sequence += 1;
					if (added_line.indexOf(item) < 0) {
						res.push({
							'line_seq': sequence,
							'combo': false,
							'combo_seq': false,
							'lines': item,
						})
						added_line.push(item);
					}
				} else {
					var orderline_in_combo = order_lines.filter(function (l) {
						return l.combo_seq == item.combo_seq;
					})
					var total_combo_amount = 0;
					var total_combo_qty = 0
					_.each(orderline_in_combo, function (line) {
						if (return_order) {
							total_combo_amount += (line.qty * line.price_unit);
						} else {
							total_combo_amount += (line.get_quantity_str() * line.get_unit_display_price());
						}
						// total_combo_amount += (line.get_quantity_str()*line.get_unit_display_price());
						var _topping_lines = self.get_orderlines().filter(function (topping) {
							return topping.related_line_id == line.fe_uid;
						})
						_.each(_topping_lines, function (l) {
							if (return_order) {
								total_combo_amount += (l.qty * l.price_unit);
							} else {
								total_combo_amount += (l.get_quantity_str() * l.get_unit_display_price());
							}
						})
						//                        total_combo_qty = parseInt((return_order? line.qty : line.quantity)/line.combo_qty);
						total_combo_qty = parseInt(line.combo_qty) || 1;
					})
					if (res.filter(function (r) { return r.combo_seq == item.combo_seq }).length == 0) {
						sequence += 1;
						res.push({
							'line_seq': sequence,
							'combo': self.pos.db.get_combo_by_id(item.combo_id),
							'combo_seq': item.combo_seq,
							'lines': orderline_in_combo,
							'total_combo_amount': total_combo_amount,
							'total_combo_qty': total_combo_qty
						})
						_.each(orderline_in_combo, function (o) {
							if (added_line.indexOf(o) < 0) {
								added_line.push(o);
							}
						})
					}
				}
			})
			return res;

		},
		//Add loyalty promotion product
		add_product_reward: function (product, new_price, is_birthday_promotion, reward = false) {
			var self = this;
			var loyalty_point_cost = reward ? reward.point_cost : 0;
			this.pos.chrome.gui.show_popup('topping_poppup', {
				'product': product,
				'is_loyalty_line': true,
				'new_price': new_price,
				'reward': reward,
				'is_birthday_promotion': is_birthday_promotion,
				'loyalty_point_cost': loyalty_point_cost,
			});
		},
		search_range_date: function (date_order_fm) {
			// Thái: Return True nếu không bật cấu hình iface_pos_return_product
			if (!this.pos.config.iface_pos_return_product) {
				return true;
			}
			var now = new Date();
			var max_date = this.pos.config.maximum_date;

			var out_of_date = new Date(date_order_fm.getFullYear(), date_order_fm.getMonth(), date_order_fm.getDate() + max_date);

			if (now >= date_order_fm && out_of_date >= now) {
				return true;
			}
			return false
		},
		cancel_reward_popup: function () {
			var numpad = this.pos.chrome.screens.products.numpad;
			numpad.clickChooseRewardLoyalty();
		},
		check_employee_coupon_using: function (code = false) {
			var order = this;
			code = code ? code : order.current_coupon_code;
			if (order.coupon_code_array.length && code) {
				var employee_coupon = order.coupon_code_array.filter(function (line) { return line == code }
				);
				if (employee_coupon.length) {
					return true;
				}
			}
			return false;
		},
		set_values_to_return: function (vals) {
			var self = this;
			var order = this.pos.get_order();
			order.order_to_return.push({
				order: vals[0][0],
				orderlines: vals[1],
				paymentlines: vals[2],
				cashier: vals[3],
			});
			order.return_origin = order.order_to_return[0].order.pos_reference;
			order.trigger('change', order);
			// self.pos.chrome.gui.show_screen('return_product_screen_widget');
		},
		get_total_list_price: function () {
			var self = this;
			var orderlines = this.get_orderlines();
			var price_total = 0;
			for (var line in orderlines) {
				var product = orderlines[line].product;
				var sub_price = product.list_price;
				//Vuong: subprice for combo line
				if (orderlines[line].combo_line_id) {
					var combo_line = self.pos.db.combo_lines.filter(function (item) { return item.id == orderlines[line].combo_line_id });
					if (combo_line.length && !combo_line[0].use_pricelist) {
						var line_detail = self.pos.db.combo_lines_detail.filter(function (line) {
							return line.sale_promo_combo_line_id[0] == combo_line[0].id && line.product_id[0] == product.id;
						})
						if (line_detail.length) {
							sub_price = line_detail[0].sub_price;
						}
					}
				}
				price_total += (sub_price * orderlines[line].get_quantity())
			}
			return price_total;
		},
		set_current_coupon_info: function (code, limit, promotion_line_id) {
			this.emp_coupon_code = code;
			this.current_coupon_code = code;
			this.current_coupon_limit = limit;
			this.current_coupon_promotion = promotion_line_id;
		},
		//Vuong: JS print define on order easy to inherit
		jspmWSStatus: function () {
			if (JSPM.JSPrintManager.websocket_status == JSPM.WSStatus.Open)
				return true;
			else {
				this.pos.chrome.gui.show_popup('alert', {
					'title': 'ERROR',
					'body': 'JSPrintManager is not installed or not running.',
				});
				return false;
			}
		},
		open_cashdrawer_via_socket: function (printer_name) {
			var self = this;
			if (self.pos.config.use_multi_printer) {
				qz.printers.find(printer_name).then(function (printer) {
					var config = qz.configs.create(printer);
					var data = ['\x10' + '\x14' + '\x01' + '\x00' + '\x05',];
					qz.print(config, data);
				}).catch(function (e) {
					self.pos.gui.show_popup('alert', {
						'title': 'ERROR',
						'body': 'Không tìm thấy máy in',
					});
				});
			}
		},
		//Vuong: bypass password when review order history
		get_order_to_return: function (order_name, type) {
			var self = this;
			var gui_order = self.pos.chrome.gui;
			rpc.query({
				model: 'pos.order',
				method: 'get_order_by_name',
				args: [order_name],
			}).then(function (vals) {
				if (vals[0]) {
					self.set_values_to_return(vals);
				} else {
					gui_order.show_popup('error', {
						'title': _t('Error'),
						'body': _t('Không tìm thấy hoá đơn trong hệ thống !!'),
					});
				}
			}, function (error) {
				error.event.preventDefault();
				gui_order.show_popup('error', {
					'title': _t('Error'),
					'body': _t('Không tìm thấy hoá đơn trong hệ thống !!'),
				});
			});
		},
		//Change cashier BE and FE on session
		change_cashier: function (employee) {
			var self = this;
			var gui_order = self.pos.chrome.gui;
			var current_cashier_id = self.pos.pos_session.cashier_id[0];
			if (employee.id == current_cashier_id) {
				return;
			}
			rpc.query({
				model: 'pos.session',
				method: 'update_cashier',
				args: [self.pos.pos_session.id, employee.id],
			}).then(function (result) {
				if (result !== true && result.length) {
					return gui_order.show_popup('alert', {
						'title': 'Cảnh báo',
						'body': result,
					});
				}
				var cashier = [employee.id, employee.name]
				self.pos.pos_session.cashier_id = cashier;
				self.pos.chrome.widget.username.renderElement();
				self.pos.chrome.widget.username.start();
				//                self.renderElement();
			}, function (error) {
				error.event.preventDefault();
				self.pos.chrome.gui.show_popup('error', {
					'title': _t('Error: Could not Save Changes'),
					'body': _t('Your Internet connection is probably down.'),
				});
			});
		},
		get_coupon_by_code: function (code, search_type, set_current_info = false) {
			var self = this;
			var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
			var gui_order = self.pos.chrome.gui;
			var backend_id = self.pos.config.warehouse_id
			if (order.coupon_code && code['code'] == order.coupon_code) {
				return gui_order.show_popup('error', _t('Coupon đã được nhập !!'));
			}

			var apply_coupon = true;
			var promotion_lines = order.get_promotion(apply_coupon);
			//apply promotion coupon already existed
			var promotion_coupon = order.get_promotion_for_coupon();
			if (promotion_coupon.length) {
				for (var i in promotion_coupon) {
					if (!promotion_lines.includes(promotion_coupon[i])) {
						promotion_lines.push(promotion_coupon[i]);
					}
				}
			}

			if (promotion_lines.length) {
				//    			order.coupon_code = code['code'];
				rpc.query({
					model: 'sale.promo.header',
					method: 'check_coupon_apply',
					args: [code, search_type, backend_id[0]],
				})
					.then(function (result_from_server) {
						var result_from_server = result_from_server;
						var error = '';
						if (!result_from_server.length) {
							return gui_order.show_popup('error', _t('Vui lòng kiểm tra lại Coupon'));
						}
						if (result_from_server[0] == 'date') {
							error = 'Coupon đã hết hạn (' + result_from_server[1] + '), Vui lòng kiểm tra lại !!';
							return gui_order.show_popup('error', _t(error));
						}
						if (result_from_server[0] == 'count') {
							//					error = 'Coupon đã hết xài hết số lần sử dụng cho phép !! (Đã sử dụng: ' +  result_from_server[1] + ' lần)';
							error = ['Mã Coupon đã được sử dụng ở',
								'Đơn hàng: ' + result_from_server[2],
								'CH sử dụng: ' + result_from_server[3] || '',
								'Ngày giờ: ' + result_from_server[4]]
							return gui_order.show_popup('alert', {
								'title': 'Cảnh báo',
								'body': error,
							})
							//					return gui_order.show_popup('error',_t(error));
						}
						var promotion_exist = false;
						var promo_line_coupon = false;
						for (var i = 0; i < promotion_lines.length; i++) {
							var promo_header_id = []
							if (promotion_lines[i].discount_id != false) {
								promo_header_id = promotion_lines[i].discount_id;
							} else {
								promo_header_id = promotion_lines[i].promotion_id;
							}
							var promo_header = order.get_promo_header_by_id(promo_header_id[0]);
							if (promo_header != false && promo_header.use_for_coupon == true && promotion_lines[i].id == result_from_server[4]) {
								order.set_promotion_for_coupon(promotion_lines[i], result_from_server[0]);
								//        						if (order.get_promotion_by_line(promotion_lines[i],result_from_server[i])){
								promotion_exist = true;
								promo_line_coupon = promotion_lines[i];
								break;
								//            					};
							}
						}
						if (promotion_exist == false) {
							//					if(check_promo){
							//						order.set_checked_promotion();
							//                	}else{
							//                		order.set_uncheck_promotion();
							//                	}
							return gui_order.show_popup('alert', {
								'title': _t('Cảnh báo'),
								'body': _t('Chương trình khuyến mãi của Coupon không khả dụng.'),
							});
						} else {
							if (result_from_server[1] === false) {
								var notify = [
									'Thẻ hợp lệ, vui lòng xác nhận để sử dụng !',
									'Số lần đã sử dụng: ' + result_from_server[2],
								]
							} else {
								var notify = [
									'Thẻ hợp lệ, vui lòng xác nhận để sử dụng !',
									'Ngày hết hạn: ' + result_from_server[1],
									'Số lần đã sử dụng: ' + result_from_server[2],
								]
							}
							gui_order.show_popup('confirm', {
								'title': _t('Coupon '),
								'body': notify,
								'error': 'Số lần còn lại: ' + result_from_server[3],
								'confirm': function () {
									order.set_coupon_code(code.code, promo_line_coupon.id);
									//		                	order.check_promoline(promo_line_coupon);
									order.use_coupon = true;
									if (set_current_info) {
										order.set_current_coupon_info(code.code, result_from_server[3], promo_line_coupon.id);
									}
									order.compute_promotion();
									self.pos.chrome.screens.products.order_widget.renderElement();
									//		                	if(check_promo){
									//    							order.set_checked_promotion();
									//		                	}
								},
								'cancel': function () {
									if (!order.coupon_code_array.length) {
										order.unset_promotion_for_coupon();
										order.compute_promotion_after_reset_price();
									}
									//					    	if(check_promo){
									//    							order.set_checked_promotaion();
									//		                	}else{
									//		                		order.set_uncheck_promotion();
									//		                	}
								}
							});
						}
					}, function (error) {
						error.event.preventDefault();
						gui_order.show_popup('error', {
							'title': _t('Error: Could not Save Changes'),
							'body': _t('Your Internet connection is probably down.'),
						});
					});
			} else {
				return gui_order.show_popup('alert', {
					'title': _t('Cảnh báo'),
					'body': _t('Chương trình khuyến mãi của Coupon không khả dụng.'),
				});
			}
		},

		check_promotion_line_with_product: function (promo_line, product, quantity) {
			var self = this;
			var order = this.pos.get_order();
			var product_price = order.get_new_price(product, quantity);
			product_price = product_price * quantity;
			var result = false;
			var val2 = 0;

			if (promo_line.product_attribute == 'product' || promo_line.product_attribute == 'product_template') {
				var check_product = false;
				if (promo_line.product_attribute == 'product') {
					if (promo_line.product_id[0] == product.id && promo_line.product_ean == product.barcode) {
						check_product = true;
					}
				} else {
					if (promo_line.product_tmpl_id[0] == product.product_tmpl_id) {
						check_product = true;
					}
				}
				if (!check_product) {
					return false
				}
			} else if (promo_line.product_attribute == 'cat' || promo_line.product_attribute == 'list_cat') {
				var category_list = JSON.parse(promo_line.categories_dom);
				if (!category_list.includes(product.categ_id[0])) {
					return false;
				}
			} else if (promo_line.product_attribute == 'combo') {
				var product_list = [];
				for (var i in promo_line.product_ids) {
					product_list.push(promo_line.product_ids[i]);
				}
				if (!product_list.includes(product.id)) {
					return false;
				}
			}

			if (promo_line.volume_type == 'qty') {
				val2 = quantity;
			} else if (promo_line.volume_type == 'amt') {
				val2 = product_price;
			} else if (promo_line.volume_type == 'amtx') {
				val2 = product_price;
			}
			result = order.check_condition(val2, promo_line);
			return result;
		},

		get_promotion_with_product_coupon: function (orderline, promo_line, promotion_limit) {
			var self = this;
			var check_benefit = false;
			var product = orderline.product;
			var disccount_value = promo_line.discount_value;
			if (promo_line.product_attribute != 'order' && (promo_line.benefit_product_id != false || promo_line.benefit_product_tmpl_id != false)) {
				if (product.id == promo_line.product_id[0] || product.product_tmpl_id == promo_line.product_tmpl_id[0]) {
					check_benefit = true;
				}
			} else if ((promo_line.benefit_type == 'cat' || promo_line.benefit_type == 'list_cat') && promo_line.benefit_categories_dom) {
				//				var benefit_categ_id = promo_line.benefit_categ_id[0];
				var benefit_category_list = JSON.parse(promo_line.benefit_categories_dom);
				if (benefit_category_list.includes(product.categ_id[0])) {
					check_benefit = true;
				}

			} else if (promo_line.benefit_type == 'list_product_template' && promo_line.benefit_product_tmpl_ids) {
				var benefit_product_tmpl_ids = []
				for (var i = 0; i < promo_line.benefit_product_tmpl_ids.length; i++) {
					benefit_product_tmpl_ids.push(promo_line.benefit_product_tmpl_ids[i]);
				}
				if (benefit_product_tmpl_ids.includes(product.product_tmpl_id)) {
					check_benefit = true;
				}
			} else if (promo_line.product_attribute == 'combo' && promo_line.product_ids) {
				var product_list = [];
				for (var i in promo_line.product_ids) {
					product_list.push(promo_line.product_ids[i]);
				}
				if (product_list.includes(product.id)) {
					check_benefit = true;
				}
			}
			if (check_benefit) {
				//				orderline.remove_discount_line(true);
				//				self.get_new_price(orderline.product, orderline.quantity, orderline);
				if (promo_line.modify_type == 'disc_value') {
					var discount_amount = disccount_value * orderline.get_quantity();
					orderline.set_discount_amount_line(discount_amount);
				} else if (promo_line.modify_type == 'disc_percent') {
					orderline.set_discount(disccount_value);
				} else {
					orderline.set_price(disccount_value);
				}
				orderline.coupon_promotion_limit = promotion_limit;
				orderline.set_promotion(promo_line.discount_id, promo_line.id);
				promo_line.is_product_coupon_promotion = true;
			}
		},

		rerender_all_line: function () {
			var orderlines = this.get_orderlines();
			for (var i = 0; i < orderlines.length; i++) {
				if (!orderlines[i].is_topping_line && orderlines[i].product.default_code != 'reward_code') {
					this.pos.chrome.screens.products.order_widget.rerender_orderline(orderlines[i]);
				}
			}
		},

		add_paymentline: function (payment_method) {
			if (this.pos.config.is_callcenter_pos) {
				return;
			}
			this.assert_editable();
			var newPaymentline = new models.Paymentline({}, { order: this, payment_method: payment_method, pos: this.pos });
			if ((!payment_method.is_cash_count && payment_method.use_for) || this.pos.config.iface_precompute_cash) {
				newPaymentline.set_amount(this.get_due());
			};
			this.paymentlines.add(newPaymentline);
			this.select_paymentline(newPaymentline);

		},
		check_origin_order_without_combo: function () {
			if (this.discount_amount) {
				return false;
			}
			var orderlines = this.get_orderlines();
			for (var i = 0; i < orderlines.length; i++) {
				if (orderlines[i].is_done_combo) {
					continue;
				}
				if (orderlines[i].discount || orderlines[i].discount_amount || orderlines[i].price < orderlines[i].old_price) {
					return false;
				}
			}
			return true;

		},
		check_has_reward_code: function () {
			var orderlines = this.get_orderlines();
			for (var i = 0; i < orderlines.length; i++) {
				if (orderlines[i].product.default_code == "reward_code") {
					return true;
				}
			}
			return false;
		},
		reset_base_price: function (apply_change) {
			var self = this;
			var order = this.pos.get_order();
			var orderlines = self.orderlines;
			for (var i = 0; i < orderlines.length; i++) {
				var product = orderlines.models[i].product;
				var quantity = orderlines.models[i].quantity;
				var line = orderlines.models[i];
				if (apply_change) {
					//dont reset price of combo
					if (line.is_done_combo) {
						continue;
					}
					if (line.is_promotion_line || line.reward_id) {
						order.remove_orderline(line);
						i -= 1;
					} else {
						if (product.lst_price != 0) {
							line.remove_discount_line();
						}
					}
					//can apply promotion
					line.set_disable_promotion(false);
				} else {
					self.get_base_price_by_line(product, quantity, line, apply_change);
					if (!line.old_price) {
						line.set_old_price(product.list_price);
					}
				}
			}
		},
		change_warehouse_call_center: function (show_payment_screen = false) {
			var self = this;
			var order = this.pos.get_order();
			rpc.query({
				model: 'pos.order',
				method: 'get_available_warehouse_callcenter',
				args: [],
			}).then(function (warehouse_ids) {
				if (warehouse_ids && warehouse_ids.length) {
					self.pos.warehouse_ids = warehouse_ids || [];
					self.pos.db.add_warehouse_ids(warehouse_ids);
					var list_warehouse = [];
					_.each(self.pos.warehouse_ids, function (wh) {
						list_warehouse.push({
							label: wh.code + ' - ' + wh.display_name,
							item: wh,
						});
					});
					self.pos.chrome.gui.show_popup('selection_warehouse', {
						'title': 'Chọn cửa hàng thực hiện',
						'list': list_warehouse,
						'is_selected': function (wh) {
							return wh.id === order.warehouse_callcenter_id;
						},
						'confirm': function (wh) {
							order.warehouse_callcenter_id = wh.id;
							order.sale_type_name = wh.code + ' - ' + wh.display_name;
							order.trigger('change', order);
							rpc.query({
								model: 'pos.order',
								method: 'get_product_lock_by_warehouse',
								args: [wh.id],
							}).then(function (vals) {
								order.locked_products = vals;
							})
							if (show_payment_screen) {
								self.pos.gui.show_screen('payment');
							}
						},
					});
				} else {
					order.locked_products = [];
					if (order.warehouse_callcenter_id) {
						order.warehouse_callcenter_id = false;
						order.sale_type_name = 'Chọn cửa hàng';
						order.trigger('change', order);
					}
					self.pos.gui.show_popup('alert', {
						'title': 'ERROR',
						'body': 'Không có cửa hàng đang mở bán',
					});
				}
			}, function (error) {
				error.event.preventDefault();
				self.pos.gui.show_popup('error', {
					'title': _t('Error: Could not Save Changes'),
					'body': _t('Your Internet connection is probably down.'),
				});
			});

		},
	});

	var _super_orderline = models.Orderline;
	models.Orderline = models.Orderline.extend({
		//Custom check to get loyalty
		check_condition_loyalty: function () {
			if (this.combo_id || this.is_manual_discount || this.product.display_name == 'Shipping Fee') {
				return false;
			}
			return true;
		},
		check_reset_price_update_qty: function () {
			if (this.product_coupon_code && this.cup_type == 'themos') {
				return false;
			}
			return true;
		},
		remove_discount_line: function (force_remove = false) {
			var self = this;
			var order = this.pos.get_order();
			if (this.product_coupon_code && this.cup_type == 'themos') {
				this.product_coupon_code = '';
				var cup_type = order.get_default_cup_by_product(this.product);
				if (cup_type == 'paper_1st') {
					cup_type = 'paper';
				}
				if (cup_type == 'plastic_1st') {
					cup_type = 'plastic';
				}
				if (this.material_name_list && this.material_name_list[0] == 'Ly giữ nhiệt') {
					var material_name_list = [];
					_.each(this.material_name_list, function (l) {
						if (l != self.material_name_list[0]) {
							material_name_list.push(l);
						}
					})
					this.set_material_name(material_name_list);
				}
				this.set_cup_type(cup_type);
				this.set_cup_type_default(cup_type);
			}
			_super_orderline.prototype.remove_discount_line.call(this, force_remove);
		},
		get_topping_list: function (get_line = false) {
			var self = this;
			var topping_list = [];
			var order = this.pos.get_order();
			var orderlines = order.get_orderlines();
			var topping_line = orderlines.filter(function (tp_line) { return tp_line.is_topping_line && tp_line.related_line_id == self.id; }
			);
			if (topping_line.length) {
				for (var i in topping_line) {
					if (get_line) {
						topping_list.push(topping_line[i]);
					} else {
						topping_list.push(topping_line[i].product.id);
					}
				}
			}
			return topping_list;
		},
		set_quantity: function (quantity, keep_price) {
			var self = this;
			var order = this.pos.get_order();
			_super_orderline.prototype.set_quantity.call(this, quantity, keep_price);
			if (this.product_coupon_code && this.cup_type == 'themos' && this.promotion_line_id) {
				var promo_line_id = self.pos.promotion_lines[this.promotion_line_id];
				order.get_promotion_with_product_coupon(this, promo_line_id[0], this.coupon_promotion_limit);
			}
		},
	});

	models.Product = models.Product.extend({
		check_get_price: function (widget) {
			var pos = widget.pos;
			if (this.pos_categ_id) {
				var categ = pos.db.get_category_by_id(this.pos_categ_id[0]);
				if (categ && categ.allow_show_original_price) {
					return true;
				}
			}
			return false
		},
	});

	var _super_payment_line = models.Paymentline.prototype;
	models.Paymentline = models.Paymentline.extend({
		initialize: function (attr, options) {
			_super_payment_line.initialize.call(this, attr, options);
			this.currency_name = this.currency_name || '';
			this.currency_origin_value = this.currency_origin_value || 0;
			this.exchange_rate = this.exchange_rate || 1;
			this.voucher_max_value = this.voucher_max_value || 0;
		},
		init_from_JSON: function (json) {
			_super_payment_line.init_from_JSON.apply(this, arguments);
			this.currency_name = json.currency_name || '';
			this.currency_origin_value = json.currency_origin_value || 0;
			this.exchange_rate = json.exchange_rate || 1;
			this.voucher_max_value = json.voucher_max_value || 0;
		},
		export_as_JSON: function () {
			var json = _super_payment_line.export_as_JSON.call(this);
			json.currency_name = this.currency_name || '';
			json.currency_origin_value = this.currency_origin_value || 0;
			json.exchange_rate = this.exchange_rate || 1;
			json.voucher_max_value = this.voucher_max_value || 0;
			return json;
		},
		set_voucher_max_value: function (value) {
			this.voucher_max_value = value;
		},
		set_currency: function (currency, value, rate) {
			this.currency_name = currency.name;
			this.currency_origin_value = parseInt(value);
			this.exchange_rate = rate;
		},

		get_amount_print_bill: function () {
			var order = this.pos.get_order();
			var lines = order.paymentlines.models;
			if (this.voucher_code) {
				var change = -order.get_total_with_tax();
				for (var i = 0; i < lines.length; i++) {
					change += lines[i].get_amount();
					if (lines[i] === this) {
						break;
					}
				}
				change = round_pr(Math.max(0, change), this.pos.currency.rounding)
				if (change) {
					return (this.amount - change);
				}

			}
			return this.amount;
		},

	});


});