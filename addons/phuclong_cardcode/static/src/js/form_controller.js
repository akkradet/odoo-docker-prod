odoo.define('phuclong_cardcode.form_controller', function (require) {
    "use strict";
    
	var core = require('web.core');
	var Dialog = require('web.Dialog');
	var Sidebar = require('web.Sidebar');
	
	var _t = core._t;
	var FormController = require('web.FormController');
    var rpc = require("web.rpc");

	FormController.include({
		reactive_partner_cardcode: function(partner_id, mode){
			var self = this;
			rpc.query({
	            model: 'res.partner',
	            method: 'button_unused_appear_code',
	            args: [partner_id],
	        }).then(function(){
				if(mode == 'delete'){
					return self.model
	                .deleteRecords([self.handle], self.modelName)
	                .then(self._onDeletedRecords.bind(self, [self.handle]));
				}else{
					self._toggleArchiveState(true);
				}
			})
//			self._toggleArchiveState(true);
			
		},
		renderSidebar: function ($node) {
	        var self = this;
			var renderer = this.renderer;
	        if (this.hasSidebar) {
	            var otherItems = [];
	            if (this.archiveEnabled && this.initialState.data.active !== undefined) {
	                var classname = "o_sidebar_item_archive" + (this.initialState.data.active ? "" : " o_hidden")
	                otherItems.push({
	                    label: _t("Archive"),
	                    callback: function () {
							if(self.modelName == 'res.partner' && renderer && renderer.state.data.appear_code_id){
								Dialog.confirm(self, _t("Customer's cardcode status will be updated into `CREATE`, are you sure you want to continue?"), {
		                            confirm_callback: self.reactive_partner_cardcode.bind(self, renderer.state.data.id, 'deactive'),
		                        });
							}else{
								Dialog.confirm(self, _t("Are you sure that you want to archive this record?"), {
		                            confirm_callback: self._toggleArchiveState.bind(self, true),
		                        });
							}
	                    },
	                    classname: classname,
	                });
	                classname = "o_sidebar_item_unarchive" + (this.initialState.data.active ? " o_hidden" : "")
	                otherItems.push({
	                    label: _t("Unarchive"),
	                    callback: this._toggleArchiveState.bind(this, false),
	                    classname: classname,
	                });
	            }
	            if (this.is_action_enabled('delete')) {
	                otherItems.push({
	                    label: _t('Delete'),
						callback: function () {
							if(self.modelName == 'res.partner' && renderer && renderer.state.data.appear_code_id){
								Dialog.confirm(self, _t("Customer's cardcode status will be updated into `CREATE`, are you sure you want to continue?"), {
		                            confirm_callback: self.reactive_partner_cardcode.bind(self, renderer.state.data.id, 'delete'),
		                        });
							}else{
								self._onDeleteRecord();
							}
	                    },
	                });
	            }
	            if (this.is_action_enabled('create') && this.is_action_enabled('duplicate')) {
	                otherItems.push({
	                    label: _t('Duplicate'),
	                    callback: this._onDuplicateRecord.bind(this),
	                });
	            }
	            this.sidebar = new Sidebar(this, {
	                editable: this.is_action_enabled('edit'),
	                viewType: 'form',
	                env: {
	                    context: this.model.get(this.handle).getContext(),
	                    activeIds: this.getSelectedIds(),
	                    model: this.modelName,
	                },
	                actions: _.extend(this.toolbarActions, {other: otherItems}),
	            });
	            return this.sidebar.appendTo($node).then(function() {
	                 // Show or hide the sidebar according to the view mode
	                self._updateSidebar();
	            });
	        }
	        return Promise.resolve();
	    },

	});
});
