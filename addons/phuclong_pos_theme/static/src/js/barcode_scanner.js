odoo.define('phuclong_pos_theme.barcode_scanner', function (require) {
    "use strict";
    var core = require('web.core');
    var AbstractField = require('web.AbstractField');
    var field_registry = require('web.field_registry');
    var FormController = require('web.FormController');
    var framework = require('web.framework');
    var rpc = require('web.rpc');
    var _t = core._t;
    
    FormController.include({
        _cashierBarcodeScanner: function (barcode, activeBarcode) {
            var self = this;
            if (!activeBarcode.handle) {
                return Promise.reject();
            }
            var record = this.model.get(activeBarcode.handle);
            var session_id = record.data.session_id.res_id;
            return rpc.query({
                model: 'wizard.pos.cashier.scanner',
                method: 'do_barcode_scan',
                args: [this.get_special_card_code(barcode),session_id],
            }).then(function (res){
                self.do_notify(res.message,res.cashier,"sticky","");
//                core.bus.trigger('close_dialogs');
				self.do_action('phuclong_pos_base.action_wizard_input_session_balance', {
		            additional_context: {'active_ids':[session_id],
										 'active_model': 'pos.session',
										 'active_id': session_id},
		        });
//                self.form_dialog_discarded();
//                setTimeout(function () {
//                    location.reload();
//                }, 1500);
            })
        },
        _loginBarcodeScanner: function (barcode, activeBarcode) {
            var self = this;
            if (!activeBarcode.handle) {
                return Promise.reject();
            }
            var record = this.model.get(activeBarcode.handle);
            return rpc.query({
                model: 'login.scanner.wizard',
                method: 'do_barcode_scan',
                args: [this.get_special_card_code(barcode), record],
            }).then(function (res){
            	if(res){
            		self.do_notify(res.message,res.cashier,"sticky","");
                    core.bus.trigger('close_dialogs');
                    framework.redirect('/web');
                    return Promise.resolve();
            	}else{
            		self.do_warn(_t('Login Error'), 'Thẻ nhân viên không hợp lệ',"sticky","");
            	}
            })
        },
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
    });
    var CashierBarcodeHandler = AbstractField.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.data = this.record.data
            var fieldName = 'cashier_barcode';
            this.trigger_up('activeBarcode', {
                name: this.name,
                notifyChange: false,
                fieldName: fieldName,
                commands: {
                    'barcode': '_cashierBarcodeScanner',
                }
            });
        },
    });

    field_registry.add('cashier_barcode_handler', CashierBarcodeHandler);
//    return CashierBarcodeHandler;
    
    var LoginBarcodeHandler = AbstractField.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.data = this.record.data
            var fieldName = 'scanner_code';
            this.trigger_up('activeBarcode', {
                name: this.name,
                notifyChange: false,
                fieldName: fieldName,
                commands: {
                    'barcode': '_loginBarcodeScanner',
                }
            });
        },
    });

    field_registry.add('login_barcode_handler', LoginBarcodeHandler);
//    return LoginBarcodeHandler;
});