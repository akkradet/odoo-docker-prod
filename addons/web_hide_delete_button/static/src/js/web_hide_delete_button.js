odoo.define('web_hide_delete_button.web_hide_delete_button', function (require) {
	"use strict";

	var rpc = require('web.rpc');
	var AbstractView = require('web.AbstractView');
	var session = require('web.session');

	AbstractView.include({

		init: function (viewInfo, params) {
			var self = this;
			this._super.apply(this, arguments);
			try {
				if (this.controllerParams && this.controllerParams.activeActions && this.controllerParams.activeActions.delete == true) {
					rpc.query({
						"model": this.controllerParams.modelName,
						"method": "check_unlink",
						"args": []
					}).then(function (unlink) {
						if (!unlink) {
							self.controllerParams.activeActions.delete = false;
						}
					});
				}
			} catch (error) {
				console.log(error);
			}
		},

	});

});
