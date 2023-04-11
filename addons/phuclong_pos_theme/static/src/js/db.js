odoo.define('phuclong_pos_theme.db', function (require) {
	"use strict";
	var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');
	var utils = require('web.utils');
	var rpc = require('web.rpc');
	var models = require('point_of_sale.models');

	PosDB.include({
		init: function(options){
	        options = options || {};
	    	this.sale_type_ids = {};
			this.size_ids = {}
			this.warehouse_ids = {}
	    	this.default_cups_by_product_tmpl = {};
	    	this.product_by_parent_code = {};
	    	this.product_cup_by_size = {};
			this.material_ids = {};
	    	this.product_topping = [];
			this.is_dollar_pos = false;
			this.windowsPrinters = [];
			this.warehouse_search_string = "";
	        this._super(options);
		},
		add_warehouse_ids: function(warehouse_ids){
			this.warehouse_search_string = '';
            for(var i = 0, len = warehouse_ids.length; i < len; i++){
                if(!this.warehouse_ids[warehouse_ids[i].id]){
	                this.warehouse_ids[warehouse_ids[i].id] = warehouse_ids[i];
	            }
                this.warehouse_search_string += this._warehouse_search_string(warehouse_ids[i]);
            }
        },
		_warehouse_search_string: function(warehouse){
	        var str =  warehouse.code + '|' + warehouse.display_name;
	        str = '' + warehouse.id + ':' + str.replace(':','') + '\n';
	        return str;
	    },
		search_warehouse: function(max_len, query){
	        try {
	            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
	            query = query.replace(/ /g,'.+');
	            var re = RegExp("([0-9]+):.*?"+utils.unaccent(query),"gi");
	        }catch(e){
	            return [];
	        }
	        var results = [];
	        for(var i = 0; i < max_len; i++){
	            var r = re.exec(utils.unaccent(this.warehouse_search_string));
	            if(r){
	                var id = Number(r[1]);
	                results.push(this.warehouse_ids[id]);
	            }else{
	                break;
	            }
	        }
	        return results;
	    },
		get_orders: function(){
	        var orders =  this.load('orders',[]);
			for(var i = 0; i<orders.length; i++){
				if(orders[i].data && orders[i].data.lines){
					_.each(orders[i].data.lines, function(line){
						line = line[2];
						if(line.cup_type == 'none'){
							line.cup_type = false;
						}
					})
				}
			}
			return orders
	    },
		check_dollar_pos: function(bool){
			this.is_dollar_pos = bool;
		},
		add_sale_types: function(sale_type_ids){
            for(var i = 0, len = sale_type_ids.length; i < len; i++){
                if(!this.sale_type_ids[sale_type_ids[i].id]){
	                this.sale_type_ids[sale_type_ids[i].id] =sale_type_ids[i];
	            }
            }
        },
		add_size_ids: function(size_ids){
            for(var i = 0, len = size_ids.length; i < len; i++){
                if(!this.size_ids[size_ids[i].id]){
	                this.size_ids[size_ids[i].id] =size_ids[i];
	            }
            }
        },
		add_material_ids:function(material_ids){
            for(var i = 0, len = material_ids.length; i < len; i++){
                if(!this.material_ids[material_ids[i].id]){
					if(material_ids[i].option_unavailable_dom){
						material_ids[i].option_unavailable_dom = material_ids[i].option_unavailable_dom.split(',');
					}else{
						material_ids[i].option_unavailable_dom = [];
					}
	                this.material_ids[material_ids[i].id] = material_ids[i];
	            }
            }
        },
        add_default_cups: function(default_cups_ids){
        	for(var i = 0, len = default_cups_ids.length; i < len; i++){
        		var cup_default = default_cups_ids[i];
	        	if(!this.default_cups_by_product_tmpl[cup_default.product_id[0]]){
	        		this.default_cups_by_product_tmpl[cup_default.product_id[0]] = [];
	            }
	            this.default_cups_by_product_tmpl[cup_default.product_id[0]].push(cup_default);
        	}
        },
        add_products: function(products){
	        var stored_categories = this.product_by_category_id;

	        if(!products instanceof Array){
	            products = [products];
	        }
			products = _.sortBy(products, 'pos_sequence', 'asc');
	        for(var i = 0, len = products.length; i < len; i++){
	            var product = products[i];
	            //Vuong: Add english name for dollar pos
	            if(this.is_dollar_pos && product.eng_name){
	            	product.display_name = product.eng_name;
	            }else{
					product.display_name = product.name
				}
				var search_string = this._product_search_string(product);
	            var categ_id = product.pos_categ_id ? product.pos_categ_id[0] : this.root_category_id;
	            product.product_tmpl_id = product.product_tmpl_id[0];
	            if(!stored_categories[categ_id]){
	                stored_categories[categ_id] = [];
	            }
	            stored_categories[categ_id].push(product.id);

	            if(this.category_search_string[categ_id] === undefined){
	                this.category_search_string[categ_id] = '';
	            }
	            this.category_search_string[categ_id] += search_string;

	            var ancestors = this.get_category_ancestors_ids(categ_id) || [];

	            for(var j = 0, jlen = ancestors.length; j < jlen; j++){
	                var ancestor = ancestors[j];
	                if(! stored_categories[ancestor]){
	                    stored_categories[ancestor] = [];
	                }
	                stored_categories[ancestor].push(product.id);

	                if( this.category_search_string[ancestor] === undefined){
	                    this.category_search_string[ancestor] = '';
	                }
	                this.category_search_string[ancestor] += search_string; 
	            }
	            this.product_by_id[product.id] = product;
	            if(product.barcode){
	                this.product_by_barcode[product.barcode] = product;
	            }
	            
	            //Phuclong: Get same product by parent_code
	            if(product.parent_code){
					if(!this.check_is_locked(product.product_tmpl_id)){
						if(!this.product_by_parent_code[product.parent_code]){
		                	this.product_by_parent_code[product.parent_code] = [];
			            }
		                this.product_by_parent_code[product.parent_code].push(product);
					}
	            }
	            //Phuclong: Get product cup by size
	            if(product.fnb_type == 'cup' && product.size_id){
	                if(!this.product_cup_by_size[product.size_id[0]]){
	                	this.product_cup_by_size[product.size_id[0]] = [];
		            }
	                this.product_cup_by_size[product.size_id[0]].push(product);
	            }
	            // Topping product
	            if(product.fnb_type == 'topping'){
	                this.product_topping.push(product);
	            }
	            this.product_by_tmpl_id[product.id] = product;
	            if (!this.product_ids_by_tmpl_id[product.product_tmpl_id]){
	            	this.product_ids_by_tmpl_id[product.product_tmpl_id] = [];
				}
	            this.product_ids_by_tmpl_id[product.product_tmpl_id].push(product);
	            
	            if (!this.products_by_categ[product.categ_id[0]]){
	            	this.products_by_categ[product.categ_id[0]] = [];
				}
	            this.products_by_categ[product.categ_id[0]].push(product.id);
	        }
	    },
	    get_product_by_parent_code: function(product){
			var self = this;
	    	if(product.parent_code){
				var products = this.product_by_parent_code[product.parent_code];
				products =  _.sortBy(products,function(product){
					var size_sequence = 0;
					if(product.size_id){
						var size = self.size_ids[product.size_id[0]];
						size_sequence = size.sequence;
					}
					return size_sequence;
				});
	            return products;
	    	}else{
	    		return [product];
	    	}
	        
		},
		_product_search_string: function(product){
	        var str = product.display_name;
	        if (product.barcode) {
	            str += '|' + product.barcode;
	        }
	        if (product.default_code) {
	            str += '|' + product.default_code;
	        }
	        if (product.description) {
	            str += '|' + product.description;
	        }
	        if (product.description_sale) {
	            str += '|' + product.description_sale;
	        }
	        if (product.short_name){
				str += '|' + product.short_name;
			}
	        var uom_relation = this.product_uom_relation_by_product_id[product.id] || [];
	        if(uom_relation.length){
	        	for (var i =0; i< uom_relation.length;i++){
	        		if(uom_relation[i].barcode){
	        			str += '|' + uom_relation[i].barcode;
	        		}
		    	}
	        }
	        
	        str  = product.id + ':' + str.replace(/:/g,'') + '\n';
	        return str;
		},
    });
});