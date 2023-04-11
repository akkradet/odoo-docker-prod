odoo.define('phuclong_restrict_logins.restrict_logins', function (require) {
    "use strict";

	var core = require('web.core');
	var config = require('web.config');
	var session = require('web.session');
	var utils = require('web.utils');
	var rpc = require('web.rpc');
	var framework = require('web.framework');
	var AbstractWebClient = require('web.AbstractWebClient');
	var ajax = require('web.ajax');
	var _t = core._t;
	
	AbstractWebClient.include({
	
		start: function () {
	        var self = this;
			self.check_tab_open = false;
			
			//Check another tab is open

	        localStorage.openpages = Date.now();
	        var onLocalStorageEvent = function(e){
	            if(e.key == "openpages"){
	                // Listen if anybody else is opening the same page!
	                localStorage.page_available = Date.now();
	            }
	            if(e.key == "page_available"){
	                self.check_tab_open = true;
	            }
	        };
	        window.addEventListener('storage', onLocalStorageEvent, false);
	
	        // we add the o_touch_device css class to allow CSS to target touch
	        // devices.  This is only for styling purpose, if you need javascript
	        // specific behaviour for touch device, just use the config object
	        // exported by web.config
	        this.$el.toggleClass('o_touch_device', config.device.touch);
	        this.on("change:title_part", this, this._title_changed);
	        this._title_changed();
	
	        var state = $.bbq.getState();
			var current_state = $.bbq.getState();
			var check_action_pos = false;
			if(Object.keys(current_state).length && current_state.action == 'point_of_sale.action_client_pos_menu'){
				check_action_pos = true;
			}
			if(current_state.menu_id && !current_state.cids){
				check_action_pos = true;
			}
	        // If not set on the url, retrieve cids from the local storage
	        // of from the default company on the user
	        var current_company_id = session.user_companies.current_company[0]
	        if (!state.cids) {
	            state.cids = utils.get_cookie('cids') !== null ? utils.get_cookie('cids') : String(current_company_id);
	        }
	        var stateCompanyIDS = _.map(state.cids.split(','), function (cid) { return parseInt(cid) });
	        var userCompanyIDS = _.map(session.user_companies.allowed_companies, function(company) {return company[0]});
	        // Check that the user has access to all the companies
	        if (!_.isEmpty(_.difference(stateCompanyIDS, userCompanyIDS))) {
	            state.cids = String(current_company_id);
	            stateCompanyIDS = [current_company_id]
	        }
	        // Update the user context with this configuration
			var old_context = session.user_context.allowed_company_ids;
			var check_reload = true;
			if (window.performance.getEntriesByType("navigation") && window.performance.getEntriesByType("navigation")[0]) {
	    		var p = window.performance.getEntriesByType("navigation")[0].type;
				if(p != 'reload'){
					check_reload = false;
				}
			}
			rpc.query({
		        model: 'res.users',
		        method: 'check_to_clear_session',
		        args: [session.uid],
//		        kwargs: {
//		            context: session.user_context,
//		        }
		    }).then(function (access_multi_sessions) {
		        if (access_multi_sessions && !old_context && !check_reload && !check_action_pos && !self.check_tab_open) {
		            console.log('Clear Session is ready.');
//					ajax.post('/web/session/logout', {});
//					session.rpc("/web/session/destroy", {});
//					session.session_logout().then(function() {
//		                framework.redirect('/web/login');
//		            });
					framework.redirect('/web/session/logout');
    				return new Promise();
		        }
			});
	        session.user_context.allowed_company_ids = stateCompanyIDS;
	        $.bbq.pushState(state);
	        // Update favicon
	        $("link[type='image/x-icon']").attr('href', '/web/image/res.company/' + String(stateCompanyIDS[0]) + '/favicon/')
	
	        return session.is_bound
	            .then(function () {
	                self.$el.toggleClass('o_rtl', _t.database.parameters.direction === "rtl");
	                self.bind_events();
	                return Promise.all([
	                    self.set_action_manager(),
	                    self.set_loading()
	                ]);
	            }).then(function () {
	                if (session.session_is_valid()) {
	                    return self.show_application();
	                } else {
	                    // database manager needs the webclient to keep going even
	                    // though it has no valid session
	                    return Promise.resolve();
	                }
	            }).then(function () {
	                // Listen to 'scroll' event and propagate it on main bus
	                self.action_manager.$el.on('scroll', core.bus.trigger.bind(core.bus, 'scroll'));
	                core.bus.trigger('web_client_ready');
	                odoo.isReady = true;
	                if (session.uid === 1) {
	                    self.$el.addClass('o_is_superuser');
	                }
	            });
	    },
	});

});