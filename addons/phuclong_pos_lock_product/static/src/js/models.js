odoo.define('phuclong_pos_lock_product.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    
    models.load_models([
        {
            model: 'pos.product.lock',
            fields: ['name','product_ids'],
            domain: function(self){
                return [
                    ['warehouse_id', '=', self.config.warehouse_id[0]]
                ];
            },
            loaded: function(self,lock){
                self.db.add_locked_product(lock);
            },
        }
    ]);
});