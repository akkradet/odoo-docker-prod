odoo.define('phuclong_pos_surcharge.pos_models', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
	var utils = require('web.utils');
	var round_pr = utils.round_precision;
    
    models.load_models([
        {
            model: 'product.surcharge.header',
            fields: [],
            domain: function(self){
                var now = moment().format('YYYY-MM-DD');
				return [
                    '|',
                    ['start_date','=',false],
                    ['start_date','<=',now],
                    '|',
                    ['end_date','=',false],
                    ['end_date','>=',now]
                ];
            },
            loaded: function(self,headers){
                _.each(headers, function(item){
                    if (item.warehouse_ids.length == 0){
                        self.db.surcharge_header[item.id] = item;
                    }
                    if(item.warehouse_ids.indexOf(self.config.warehouse_id[0]) >=0){
                        self.db.surcharge_header[item.id] = item;
                    }
                })
            },
        },
        {
            model: 'product.surcharge.line',
            fields: [],
            loaded: function(self,surcharge_lines){
                _.each(surcharge_lines, function(item){
                    if(self.db.surcharge_header[item.surcharge_header_id[0]]){
                        self.db.surcharge_line[item.id] = item;
                    }
                })
            },
        }
    ]);
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
    	initialize: function() {
            _super_order.initialize.apply(this,arguments);
            this.total_surcharge = this.total_surcharge || 0;
        },
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.call(this);
            json.total_surcharge = this.total_surcharge || 0;
            return json;
        },
        init_from_JSON: function(json){
            _super_order.init_from_JSON.apply(this,arguments);
            this.total_surcharge = json.total_surcharge || 0;
        },
        compute_surcharge_order: function(){
            var self = this;
            var orderlines = this.get_orderlines();
            var headers = this.check_surcharge_program();
            var total_surcharge = 0;
            _.each(orderlines, function(line){
                line.compute_surcharge_line(headers);
                total_surcharge += parseInt(line.amount_surcharge);
            })
            self.total_surcharge = total_surcharge;
        },
        check_surcharge_program: function(){
            var surcharge_headers = this.pos.db.surcharge_header;
            var sale_type_id = this.sale_type_id;
            var header = [];
            _.each(surcharge_headers, function(item){
                if (item.sale_type_ids.length == 0 || item.sale_type_ids.indexOf(sale_type_id) >= 0){
                    header.push(item);
                }
            })
            return header;
        },
        get_total_with_tax: function() {
            var total = this.get_total_without_tax() + this.get_total_tax() + this.discount_amount + this.total_surcharge;
			return round_pr(total, this.pos.currency.rounding);
        },
    });
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr, options) {
            _super_orderline.initialize.call(this,attr,options);
            this.amount_surcharge =  this.amount_surcharge || 0;
        },
        export_as_JSON: function(){
            var json = _super_orderline.export_as_JSON.call(this);
            json.amount_surcharge =  this.amount_surcharge || 0;
            return json;
        },
        init_from_JSON: function(json){
            _super_orderline.init_from_JSON.apply(this,arguments);
            this.amount_surcharge =  json.amount_surcharge || 0;
        },
        compute_surcharge_line: function(headers){
            var self = this;
            self.amount_surcharge = 0;
            _.each(headers, function(header){
                _.each(header.surcharge_line_ids, function(line){
                    var surcharge_line = self.pos.db.surcharge_line[line];
                    var loyalty_discount = self.get_loyalty_discount() || 0;
                    // Check if surcharge apply for combo
                    if (surcharge_line.apply_on == 'combo' && surcharge_line.combo_ids.indexOf(self.combo_id) >= 0 && self.is_done_combo){
                        var combo_line = self.pos.db.combo_lines.filter(function(item){return item.id == self.combo_line_id});
                        var surcharge_value = (surcharge_line.surcharge_percent/100)*self.price*self.quantity;
                        self.amount_surcharge = parseInt(surcharge_value * (100- loyalty_discount)/100);
                    }
                    // Check if surcharge apply for category
                    var product = self.product;
                    if(surcharge_line.apply_on == 'category' && !self.combo_id && surcharge_line.categories_dom.includes(product.categ_id[0])){
                        // (surcharge_percent/100) * price_unit * qty
                        var surcharge_value = (surcharge_line.surcharge_percent/100)*self.quantity*self.price;
                        self.amount_surcharge = parseInt(surcharge_value * (100- loyalty_discount)/100);
                    }
                })
            })
        }
    });
});