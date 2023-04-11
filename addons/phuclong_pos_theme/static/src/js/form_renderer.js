odoo.define('phuclong_pos_theme.form_renderer', function (require) {
    "use strict";
    
    var core = require('web.core');
    var data = require('web.data');
    var utils = require('web.utils');
    var FormView = require('web.FormView');
    var Widget = require('web.Widget');
    var session = require('web.session');
    var _t = core._t;
    var QWeb = core.qweb;
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;
    var FormRenderer = require('web.FormRenderer');
	var FormController = require('web.FormController');
    var rpc = require("web.rpc");
	var ListView = require('web.ListRenderer');

	function is_xml(subreceipt){
        return subreceipt ? (subreceipt.split('\n')[0].indexOf('<!DOCTYPE QWEB') >= 0) : false;
    }
	function render_xml(subreceipt){
        if (!is_xml(subreceipt)) {
            return subreceipt;
        } else {
            subreceipt = subreceipt.split('\n').slice(1).join('\n');
            var qweb = new QWeb2.Engine();
                qweb.debug = core.debug;
                qweb.default_dict = _.clone(QWeb.default_dict);
                qweb.add_template('<templates><t t-name="subreceipt">'+subreceipt+'</t></templates>');
            
            return qweb.render('subreceipt',{'pos':self.pos,'widget':self.pos.chrome,'order':self, 'receipt': receipt}) ;
        }
    }
    
    FormRenderer.include({
        events: _.extend({}, FormRenderer.prototype.events, {
            "click .print_date_revenue_report": "get_date_revenue_by_warehouse",
			"click .print_pos_order_report": "print_pos_order_report",
        }),
        get_date_revenue_by_warehouse: function(){
            var self = this;
            rpc.query({
                    model: 'pos.session',
                    method: 'get_date_revenue_by_warehouse',
                    args: [this.state.data.warehouse_id.res_id, this.state.data.date.toJSON()],
                })
                .then(function (result) {
//					core.bus.trigger('close_dialogs');
                    var values = {
                        widget:self,
                        warehouse_name: result.warehouse_name,
                        date_start_string: result.date_start_string,
                        bill_products_by_cate: result.bill_products_by_cate,
                        canceled_order_total: result.canceled_order_total,
                        canceled_order_len: result.canceled_order_len,
                        num_of_order: result.num_of_order,
                        num_of_partner: result.num_of_partner,
                        avg_total_order: result.avg_total_order,
                        total_surchase: result.total_surchase,
                        discount_info: result.discount_info,
                        gift_info: result.gift_info,
                        order_by_journal: result.order_by_journal,
                        sum_list_price: 0,
                        total_discount: 0,
                        session_amount: result.session_amount,
//                        plastic_cup: result.plastic_cup,
//                        paper_cup: result.paper_cup,
						cups: result.cups,
                        lids: result.lids,
						list_no_cup: result.list_no_cup,
                        skill_paper_cup: result.skill_paper_cup,
                        skill_plastic_cup: result.skill_plastic_cup,
//                        cup_plastic: result.cup_plastic,
//                        cup_paper: result.cup_paper,
                        change_cup_plastic: result.change_cup_plastic,
                        change_cup_paper: result.change_cup_paper,
						combo_list: result.combo_list,
                        user_name: result.user_name,
						draft_bill: result.draft_bill,
           				auto_paid_bill: result.auto_paid_bill,
                        
                    }
                    var el_str = QWeb.render('PrintDateBillWidget',values);
                    var div_html = $('div.date_revenue_report');
                    if(div_html.length == 0){
                        div_html = document.createElement("div");
                        div_html.classList.add('date_revenue_report');
                    }
                    $('body .o_action_manager').after(div_html);
                    $('div.date_revenue_report').html(el_str);
                    $('body .o_action_manager').addClass('o_hidden');
					setTimeout(function(){
						window.print();
						$('body .o_action_manager').removeClass('o_hidden');
                    	$('div.date_revenue_report').empty();
					}, 500);
                    
                });
        },
        _renderReportButton: function (node) {
            var $print_button = $('<button>')
                .text(node.children[0])
                .addClass('btn btn-binary print_date_revenue_report')
                .css('background-color', '#00A09D')
                .css('color', '#fff');
            this._handleAttributes($print_button, node);
            this._registerModifiers(node, this.state, $print_button);
            return $print_button;
        },
		_renderPosOrderReportButton: function (node) {
            var $print_button = $('<button>')
                .text(node.children[0])
                .addClass('btn btn-binary print_pos_order_report')
                .css('background-color', '#00A09D')
                .css('color', '#fff');
            this._handleAttributes($print_button, node);
            this._registerModifiers(node, this.state, $print_button);
            return $print_button;
        },
        _renderHeaderButtons: function (node) {
            var self = this;
            var $buttons = $('<div>', {class: 'o_statusbar_buttons'});
            _.each(node.children, function (child) {
                if (child.tag === 'button') {
                    $buttons.append(self._renderHeaderButton(child));
                }
                if (child.tag === 'div' && child.attrs.class === 'print-direct') {
                    $buttons.append(self._renderPrintButton(child));
                }
                if (child.tag === 'div' && child.attrs.class === 'print_date_revenue_report') {
                    $buttons.append(self._renderReportButton(child));
                }
                if (child.tag === 'div' && child.attrs.class === 'print-picking-receipt') {
                    $buttons.append(self._renderPicking_Receipt(child));
                }
				if (child.tag === 'div' && child.attrs.class === 'print-pos-order') {
                    $buttons.append(self._renderPosOrderReportButton(child));
//					self.render_config_logo();
                }
            });
            return $buttons;
        },
        format_value_with_precision: function(amount){
            return this.format_value(parseInt(amount));
        },
		format_pr: function(value,precision=false){
			if(!value){
				value = 0;
			}
	        var decimals = precision > 0 ? Math.max(0,Math.ceil(Math.log(1.0/precision) / Math.log(10))) : 0;
	        return value.toFixed(decimals);
	    },
		get_config_image_url: function(config){
	        return window.location.origin + '/web/image?model=pos.config&field=logo&id='+config;
	    },
        get_time_start: function(time){
            var time_start = new Date(time);
            var minute_start = time_start.getMinutes();
//            var hour_start = time_start.getHours() + 7;
			var hour_start = time_start.getHours()
            var year_start = time_start.getFullYear();
            var date_start = time_start.getDate();
            var start_at = new Date(year_start, time_start.getMonth(), date_start, hour_start, minute_start);
            var start_at_hour = start_at.getHours()
            var month_start = start_at.getMonth() + 1;
            month_start = month_start.toString()
            if(month_start.length==1){
                month_start = '0' + month_start;
            }
            return start_at.getDate().toString() + '/' + month_start + '/' + year_start.toString() + ' ' +  start_at_hour.toString() + ':' + minute_start.toString();
        },
        show_revenue:function(warehouse){
            var self = this;
            var datarecord = self.state.data;
            //General:
            var pos_name = datarecord.config_id.data.display_name;
            if(pos_name.includes('(')){
                pos_name = pos_name.substring(0, pos_name.indexOf('('));
            }
            var date_start_string = '';
            var time_starts =  datarecord.start_at || false;
            if(time_starts){
                date_start_string = this.get_time_start(time_starts);
            }
            var session_name = datarecord.name || false;
            var total = datarecord.cash_register_total_entry_encoding + datarecord.amount_paid_by_bank
            var amount_total = this.format_value_with_precision(total);
            //Payment method:
            var cash_amount = this.format_value_with_precision(datarecord.cash_register_total_entry_encoding) || 0;
            var amount_paid_by_bank = this.format_value_with_precision(datarecord.amount_paid_by_bank) || 0;
            var values = {
                widget:self,
                //General:
                pos_name:pos_name,
                date_start_string:date_start_string,
                warehouse_code:warehouse.code,
                warehouse_name:warehouse.name,
                session_name:session_name,
                amount_total: amount_total,
                //Payment method:
                cash_amount: cash_amount,
                amount_paid_by_bank:amount_paid_by_bank,
            };
            rpc.query({
                model: 'pos.session',
                method: 'get_session_detail',
                args: [this.state.data.id],
            })
            .then(function (result) {
                values.order_by_cashier = result.order_by_cashier,
                values.bill_products_by_cate = result.bill_products_by_cate;
                values.canceled_order_total = result.canceled_order_total;
                values.num_of_order = result.num_of_order;
                values.num_of_partner = result.num_of_partner;
                values.avg_total_order = result.avg_total_order;
                values.total_surchase = result.total_surchase;
                values.discount_info = result.discount_info;
                values.gift_info = result.gift_info;
                values.order_by_journal = result.order_by_journal;
				values.combo_list = result.combo_list;
                var el_str = QWeb.render('PrintBillWidget',values);
                $('.print-bill-session').html(el_str);
                setTimeout(function(){
					window.print()
                }, 500);
            });
        },
		
		//POS Order Backend print
		get_orderlines_groupby_combo: function(orderlines){
            var self = this;
            var res = [];
            var added_line = [];
            var order_lines = orderlines.filter(function(item){return item.is_topping_line == false});
			var sequence = 0;						
            _.each(_.sortBy(order_lines, 'id', 'asc'), function(item){
                if (!item.is_done_combo){
					sequence += 1;
                    if(added_line.indexOf(item)<0){
                        res.push({
							'line_seq': sequence,
                            'combo':false,
                            'combo_seq': false,
                            'lines': item,
                        })
                        added_line.push(item);
                    }
                } else{
                    var orderline_in_combo = order_lines.filter(function(l){
                        return l.combo_seq == item.combo_seq;
                    })
                    var total_combo_amount = 0;
                    var total_combo_qty = 0
					_.each(orderline_in_combo, function(line){
                        total_combo_amount += (line.qty*line.price_unit);
                        var _topping_lines = order_lines.filter(function(topping){
                            return topping.related_line_id == line.fe_uid;
                        })
                        _.each(_topping_lines, function(l){
                            total_combo_amount += (l.qty*l.price_unit);
                        })
//                        total_combo_qty = parseInt(line.qty/line.combo_qty);
						total_combo_qty = parseInt(line.combo_qty) || 1;
                    })
                    if(res.filter(function(r){return r.combo_seq == item.combo_seq}).length == 0){
						sequence += 1;
                        res.push({
							'line_seq': sequence,
                            'combo_name':item.combo_name,
                            'combo_seq': item.combo_seq,
                            'lines': orderline_in_combo,
                            'total_combo_amount': total_combo_amount,
                            'total_combo_qty': total_combo_qty
                        })
                        _.each(orderline_in_combo, function(o){
                            if(added_line.indexOf(o)<0){
                                added_line.push(o);
                            }
                        })
                    }
                }
            })
            return res;

        },
		print_pos_order_report: function() {
            var self = this;
			var datarecord = self.state.data;
            var order_name = datarecord.name;
            rpc.query({
	            model: 'pos.order',
	            method: 'get_order_by_name',
	            args: [order_name],
	        }).then(function(vals){
				var order_to_return = {
	                order:vals[0][0],
	                orderlines:vals[1],
	                paymentlines:vals[2],
	                cashier:vals[3],
					partner:vals[4]
	            };
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
	            var partner = order_to_return.partner;
	            if(partner.length){
					order_id.partner_return_id = partner[0];
	                var partner_name = partner[0].name;
	                var partner_mobile = partner[0].mobile;
	                var partner_ref = partner[0].ref || false;
	            }
	            var orderlines = order_to_return.orderlines;
	            
	            for(var line in orderlines){
	                orderlines[line].new_price = orderlines[line].price_subtotal_incl/orderlines[line].qty;
					orderlines[line].price_subtotal_no_discount = orderlines[line].price_unit*orderlines[line].qty;
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
//						logo:self.get_config_image_url(order_id.config_id),
	            };
		    	receipt_return.header_xml = render_xml(order_id.receipt_header);
		    	receipt_return.footer_xml = render_xml(order_id.receipt_footer);
				orderlines = _.sortBy(orderlines, 'id', 'asc');
				var orderlines_by_combo = self.get_orderlines_groupby_combo(orderlines)
	            var el_str = QWeb.render('PosOrderBillBackend',{
	                    widget:self,
						datarecord:datarecord,
	                    order: order_id,
	                    receipt_return: receipt_return,
	                    orderlines: orderlines_by_combo,
						orderlines_single: orderlines,
	                    paymentlines: order_to_return.paymentlines,
                });

//                var div_html = $('div.pos_order_report');
//                if(div_html.length == 0){
//                    div_html = document.createElement("div");
//                    div_html.classList.add('pos_order_report');
//                }
				rpc.query({
                    model:'pos.order',
                    method: 'set_count_of_print_bill',
                    args: [order_id.name],
                })
//                $('body .o_action_manager').after(div_html);
//                $('div.pos_order_report').html(el_str);
//                setTimeout(function(){}, 1000);
//                $('body .o_action_manager').addClass('o_hidden');
//                self.print_bill();
				self.connect_qz_via_socket(el_str);
//                $('body .o_action_manager').removeClass('o_hidden');
//                $('div.pos_order_report').empty();

            });

        },

		render_config_logo: function() {
            var self = this;
			var datarecord = self.state.data;
            var order_name = datarecord.name;
            rpc.query({
	            model: 'pos.order',
	            method: 'get_order_config_logo_by_name',
	            args: [order_name],
	        }).then(function(vals){
	            var el_str = QWeb.render('RenderConfigLogo',{
	                logo:self.get_config_image_url(vals[0]),
					footer_xml: render_xml(vals[1])
                });
                var div_html = $('div.pos_order_report_logo');
                if(div_html.length == 0){
                    div_html = document.createElement("div");
                    div_html.classList.add('pos_order_report_logo');
                }
                $('body .o_action_manager').after(div_html);
                $('div.pos_order_report_logo').html(el_str);
//                $('div.pos_order_report_1').empty();

            });

        },

		connect_qz_via_socket: function(html){
			var self = this;
			if (!qz.websocket.isActive()){
		        qz.websocket.connect().then(function() {
					self.print_qz_backend(html)
				}).catch(function() {
					self.do_warn('Lỗi', 'Không tìm thấy máy in bill',"sticky","");
	            });
		    }else{
				self.print_qz_backend(html)
			}
        },
		print_qz_backend: function(html){
			var self = this;
			qz.printers.find('POS Order').then(function(printer) {
                var options = { margins: { top: 0, right: 0, bottom: 0, left: 0.0833333333 }};
                var config = qz.configs.create(printer, options);
//				config.config.scaleContent = false;
                var data = [{
                    type: 'pixel',
					format: 'html',
					flavor: 'plain',
                    data: html
                }];  // Raw ZPL
				config.config.scaleContent = false;
                config.config.rasterize = false;
                data[0].options = {
                    pageWidth: 2.85,
                }
                qz.print(config, data);
            }).catch(function() {
				self.do_warn('Lỗi', 'Không tìm thấy máy in bill',"sticky","");
            });
		}

    });

	FormController.include({
		_onButtonClicked: function (ev) {
	        var self = this;
	        this._super.apply(this, arguments);
			if(ev.data && ev.data.attrs && ev.data.record && ev.data.record.data){
				var data = ev.data.record.data;
				//Print report
				if(ev.data.attrs.name == 'print_date_revenue_report'){
					self.renderer.get_date_revenue_by_warehouse();
				}
				//Open Session
				if(ev.data.attrs.name == 'set_balance_start' && data.balance_start){
					self.open_cashdrawer_via_socket();
				}
				//Close Session
				if(ev.data.attrs.name == 'action_pos_session_closing_control' && data.cash_register_balance_end){
					rpc.query({
			            model: 'pos.session',
			            method: 'check_condition_open_cashbox',
			            args: [data.id],
			        }).then(function(vals){
			            if(vals){
							self.open_cashdrawer_via_socket();
						}
		            });
				}
			}
	    },
		open_cashdrawer_via_socket: function(){
			var self = this;
			if (!qz.websocket.isActive()){
		        qz.websocket.connect().then(function() {
					self.apply_kick_code()
				})
		    }else{
				self.apply_kick_code()
			}
        },
		apply_kick_code: function(){
			qz.printers.find('POS Order').then(function(printer) {
                var config = qz.configs.create(printer);
                var data = ['\x10' + '\x14' + '\x01' + '\x00' + '\x05',];
                qz.print(config, data);
            }).catch(function(e) {
                return
            });
		}

	});
	
    ListView.include({
        _onRemoveIconClick: function (event) {
			if(this.state && this.state.model == "wizard.modify.payment.line"){
				var result = confirm("Bạn có chắc chắn muốn xóa dòng thanh toán này ?");
             	if (result) {
					return this._super(event);
				}
			}else{
				return this._super(event);
			}
	    },

    });
});
