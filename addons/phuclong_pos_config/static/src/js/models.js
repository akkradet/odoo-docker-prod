odoo.define('phuclong_pos_config.pos_models_config', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var rpc = require('web.rpc');
    var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');

	PosDB.include({
        add_order: function(order){
            var order_id = order.uid;
            var orders  = this.load('orders',[]);
            // if the order was already stored, we overwrite its data
            for(var i = 0, len = orders.length; i < len; i++){
                // Thai: Không ghi đè đơn hàng nếu đang bật option Sandbox để test performance
                if (!globalThis.posmodel.config.is_sandbox_env){
                    if(orders[i].id === order_id){
                        orders[i].data = order;
                        this.save('orders',orders);
                        return order_id;
                    }
                }
            }

            // Only necessary when we store a new, validated order. Orders
            // that where already stored should already have been removed.
            this.remove_unpaid_order(order);
            orders.push({id: order_id, data: order});
            this.save('orders',orders);
            return order_id;
        }
    })
    models.PosModel = models.PosModel.extend({
        push_order: function (order, opts) {
            opts = opts || {};
            var self = this;
			var order_json = {};
			if(order){
				order_json = order.export_as_JSON();
			}
            return new Promise(function (resolve, reject) {
                self.flush_mutex.exec(function () {
					if (order) {
		                if (self.config.is_sandbox_env){
		                    var order_to_duplicated = self.config.max_order_to_create;
		                    for(var i=0;i<order_to_duplicated;i++){
		                        self.db.add_order(order_json);
		                    }
		                } else{
		                    self.db.add_order(order_json);
		                }
		            }
                    var flushed = self._flush_orders(self.db.get_orders(), opts);
    
                    flushed.then(resolve, reject);
    
                    return flushed;
                });
            });
        }
    })
});
