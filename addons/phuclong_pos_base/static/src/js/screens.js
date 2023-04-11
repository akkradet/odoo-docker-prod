odoo.define('phuclong_pos_base.screens', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var core = require('web.core');
var utils = require('web.utils');
var rpc = require('web.rpc');
var screens = require('point_of_sale.screens');
var PopupWidget = require('point_of_sale.popups');

var QWeb = core.qweb;
var _t = core._t;

var round_pr = utils.round_precision;


screens.NumpadWidget.include({

    clickSetNote: function() {
    	var self = this;
    	var order = self.pos.get_order();
    	var sale_type = false;
    	if(order.sale_type_id){
    		sale_type = order.get_sale_type_by_id(order.sale_type_id);
    	}
    	if(sale_type && sale_type.use_for_call_center){
    		self.gui.show_popup('text2area',{
                title: _t('Ghi chú'),
                confirm: function(note, mobile) {
					order.note_address = note;
					order.note_mobile = mobile;
                	if(mobile && note){
                		note = mobile + ' - ' + note;
                	}
                	if(!note){
                		note = mobile;
                	}
                	order.set_note(note);
                },
            });
    	}else{
    		self.gui.show_popup('textarea',{
                title: _t('Ghi chú'),
                value:   order.get_note(),
                confirm: function(note) {
                	order.set_note(note);
                },
            });
    	}
    },
});

var Text2AreaPopupWidget = PopupWidget.extend({
    template: 'Text2AreaPopupWidget',
    
    show: function(options){
		var self = this;
        options = options || {};
		var today = moment();
		var next_day_1 = moment(today).add(1, 'days');
		var next_day_2 = moment(today).add(2, 'days');
		this.next_day_list = [next_day_1.format('DD/MM/YYYY'), next_day_2.format('DD/MM/YYYY')]
		
        this._super(options);

        this.renderElement();

		this.$('.timepicker').timepicker({
		    timeFormat: 'h:mm',
		    interval: 60,
		    minTime: '10',
		    maxTime: '6:00pm',
		    defaultTime: '11',
		    startTime: '10:00',
		    dynamic: false,
		    dropdown: false,
		    scrollbar: false
		});
		
		var order = this.pos.get_order();
		this.$('textarea').val(order.note_address)
		this.$('input.mobile').val(order.note_mobile)
		setTimeout(function () {
	        self.$('textarea').focus();
	    }, 100);
    },
    click_confirm: function(){
        var value = this.$('textarea').val();
        var value_text = this.$('input.mobile').val();
		if(!value || !value_text){
			var error_mess = this.$el.find('.note-error-mess')[0];
        	error_mess.textContent  = "Vui lòng nhập đủ các thông tin";
			return;
		}
        this.gui.close_popup();
        if( this.options.confirm ){
            this.options.confirm.call(this,value, value_text);
        }
    },
});
gui.define_popup({name:'text2area', widget: Text2AreaPopupWidget});

gui.Gui.include({
	_show_first_screen: function () {
		var self = this;
        this._super();
		window.onbeforeunload = function(e)
	    {	
			var pending_not_payment = self.pos.get_order_list();
			for(var i in pending_not_payment){
				if(!pending_not_payment[i].finalized){
					var orderlines = pending_not_payment[i].get_orderlines();
					if(orderlines.length){
						return 'Đơn hàng đang order dở dang sẽ không được lưu lại, bạn có muốn tiếp tục?'
					}
				}
			}
	    };
    },
	remove_all_pending_orders: function(){
		var pending_not_payment = this.pos.get_order_list();
		for (var i=0; i < pending_not_payment.length; i++){
			if(!pending_not_payment[i].finalized){
				var orderlines = pending_not_payment[i].get_orderlines();
				if(orderlines.length){
					pending_not_payment[i].destroy({'reason':'abandon'});
					i-=1;
				}
			}
		}
	},
	close: function() {
        var self = this;
        var pending = this.pos.db.get_orders().length;

		var pending_not_payment = this.pos.get_order_list();
		for(var i in pending_not_payment){
			if(!pending_not_payment[i].finalized){
				var orderlines = pending_not_payment[i].get_orderlines();
				if(orderlines.length){
					return self.show_popup('confirm', {
	                    'title': ('Cảnh báo'),
	                    'body':  'Đơn hàng đang order dở dang sẽ không được lưu lại, bạn có muốn tiếp tục?',
	                    'confirm': function() {
							self.remove_all_pending_orders();
	                        self._close();
	                	},
						'cancel': function() {
							var close_button = self.chrome.widget.close_button;
							close_button.$el.removeClass('confirm');
                            close_button.$el.text(_t('Close'));
							close_button.confirmed = false;
						},
                	});
				}
			}
		}

        if (!pending) {
            this._close();
        } else {
            var always = function () {
                var pending = self.pos.db.get_orders().length;
                if (!pending) {
                    self._close();
                } else {
                    var reason = self.pos.get('failed') ?
                                ('Some orders could not be submitted to '+
                                     'the server due to configuration errors. '+
                                     'You can exit the Point of Sale, but do '+
                                     'not close the session before the issue '+
                                     'has been resolved.') :
                                ('Some orders could not be submitted to '+
                                     'the server due to internet connection issues. '+
                                     'You can exit the Point of Sale, but do '+
                                     'not close the session before the issue '+
                                     'has been resolved.');

                    self.show_popup('confirm', {
                        'title': ('Offline Orders'),
                        'body':  reason,
                        'confirm': function() {
                            self._close();
                        },
                    });
                }
            };
            this.pos.push_order().then(always, always);
        }
    },
});

});
