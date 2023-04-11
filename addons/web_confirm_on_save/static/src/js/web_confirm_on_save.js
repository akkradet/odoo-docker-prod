odoo.define('web_confirm_on_save.web_confirm_on_save', function (require) {
"use strict";

var ajax = require('web.ajax');
var AbstractView = require('web.AbstractView');
var FormController = require('web.FormController');
var Dialog = require('web.Dialog');
var session = require('web.session');

AbstractView.include({
	
	init: function (viewInfo, params) {
    	var self = this;
    	this._super.apply(this, arguments);
    	var confirm =  this.arch.attrs.confirm ? this.arch.attrs.confirm : false;
    	var alert =  this.arch.attrs.alert ? this.arch.attrs.alert : false;
    	self.controllerParams.activeActions.confirm = confirm;
    	self.controllerParams.activeActions.alert = alert;
    },

});

FormController.include({
	
	check_condition: function (modelName, record_id ,data_changed) {
        var def = this._rpc({
            "model": modelName,
            "method": "check_condition_show_dialog",
            "args": [record_id ,data_changed]
        });
        return def;
    },
	
	_onSave: function (ev) {
		var self = this;
		var modelName = this.modelName ? this.modelName : false;
		var record = this.model.get(this.handle, {raw: true});
		var data_changed = record ? record.data : false;
		var record_id = data_changed && data_changed.id ? data_changed.id : false;
		var confirm = self.activeActions.confirm;
		var alert =  self.activeActions.alert;
		function saveAndExecuteAction () {
			ev.stopPropagation(); // Prevent x2m lines to be auto-saved
			self._disableButtons();
			self.saveRecord().then(self._enableButtons.bind(self)).guardedCatch(self._enableButtons.bind(self));
	    }
		if(modelName && record && (confirm || alert)){
			self.check_condition(modelName, record_id, data_changed).then(function(opendialog){
	        	if(!opendialog){
	        		saveAndExecuteAction();
	        	}else{
	        		if(confirm){
	        			var def = new Promise(function (resolve, reject) {
	        	            Dialog.confirm(self, confirm, {
	        	                confirm_callback: saveAndExecuteAction,
	        	            }).on("closed", null, resolve);
	        	        });
	        		}else{
        				var def = new Promise(function (resolve, reject) {
        		            Dialog.alert(self, alert, {
        		                confirm_callback: saveAndExecuteAction,
        		            }).on("closed", null, resolve);
        		        });
	        			saveAndExecuteAction();
	        		}
	        	}
	        });
		}else{
			saveAndExecuteAction();
		}
	},

});

});
