odoo.define('phuclong_pos_loyalty.db', function (require) {
	"use strict";
	var PosDB = require('point_of_sale.DB');
	var screens = require('point_of_sale.screens');
	var core = require('web.core');
	var utils = require('web.utils');

	PosDB.include({
		init: function(options){
	        options = options || {};
	        this.partner_by_card_code_id = {};
	        this.card_code_by_barcode = {};
			this.card_code_by_id = {};
			this.states = {};
            this.districts = {};
            this.wards = {};
	        this._super(options);
		},
		
        add_states:function(states){
            this.states = states;
        },
        add_districts:function(districts){
            this.districts = districts;
        },
        add_wards:function(wards){
            this.wards = wards;
        },
		get_district_by_state:function(state_id){
	        var district_obj = this.districts.filter(function(district){
	            return district.state_id[0] == state_id;
	        });
	        return district_obj;
	    },

        get_ward_by_district:function(district_id){
	        var ward_obj = this.wards.filter(function(ward){
	            return ward.district_id[0] == district_id;
	        });
            return ward_obj
        },
		
		add_card_code: function(card_code_ids){
			var updated_count = 0; 
        	for(var i = 0, len = card_code_ids.length; i < len; i++){
        		var card_code = card_code_ids[i];
        		this.card_code_by_barcode[card_code.hidden_code] = card_code;
				this.card_code_by_id[card_code.id] = card_code;
				updated_count += 1;
        	}
			return updated_count;
        },

		_partner_search_string: function(partner){
	        var str =  partner.name || '';
	        if(partner.barcode){
	            str += '|' + partner.barcode;
	        }
	        if(partner.address){
	            str += '|' + partner.address;
	        }
	        if(partner.phone){
	            str += '|' + partner.phone.split(' ').join('');
	        }
	        if(partner.mobile){
	            str += '|' + partner.mobile.split(' ').join('');
	        }
//			if(partner.appear_code_id){
//	            str += '|' + partner.appear_code_id[1].split(' ').join('');
//	        }
	        if(partner.email){
	            str += '|' + partner.email;
	        }
	        if(partner.vat){
	            str += '|' + partner.vat;
	        }
	        str = '' + partner.id + ':' + str.replace(':','') + '\n';
	        return str;
	    },
		
		add_partners: function(partners){
	        var updated_count = 0;
	        var new_write_date = '';
	        var partner;
	        for(var i = 0, len = partners.length; i < len; i++){
	            partner = partners[i];

	            var local_partner_date = (this.partner_write_date || '').replace(/^(\d{4}-\d{2}-\d{2}) ((\d{2}:?){3})$/, '$1T$2Z');
	            var dist_partner_date = (partner.write_date || '').replace(/^(\d{4}-\d{2}-\d{2}) ((\d{2}:?){3})$/, '$1T$2Z');
	            if (    this.partner_write_date &&
	                    this.partner_by_id[partner.id] &&
	                    new Date(local_partner_date).getTime() + 1000 >=
	                    new Date(dist_partner_date).getTime() ) {
	                // FIXME: The write_date is stored with milisec precision in the database
	                // but the dates we get back are only precise to the second. This means when
	                // you read partners modified strictly after time X, you get back partners that were
	                // modified X - 1 sec ago. 
	                continue;
	            } else if ( new_write_date < partner.write_date ) { 
	                new_write_date  = partner.write_date;
	            }
	            if (!this.partner_by_id[partner.id]) {
	                this.partner_sorted.push(partner.id);
	            }
	            this.partner_by_id[partner.id] = partner;

	            updated_count += 1;
	        }

	        this.partner_write_date = new_write_date || this.partner_write_date;

	        if (updated_count) {
	            // If there were updates, we need to completely 
	            // rebuild the search string and the barcode indexing

	            this.partner_search_string = "";
	            this.partner_by_barcode = {};
	            this.partner_by_card_code_id = {};

	            for (var id in this.partner_by_id) {
	                partner = this.partner_by_id[id];

	                if(partner.barcode){
	                    this.partner_by_barcode[partner.barcode] = partner;
	                }
	                if(partner.appear_code_id){
	                    this.partner_by_card_code_id[partner.appear_code_id[0]] = partner;
	                }
	                
                	partner.address = (partner.street || '') +', '+ 
									  (partner.ward_id ?  partner.ward_id[1] : '')   +', '+ 
	                				  (partner.district_id ?  partner.district_id[1] : '')   +', '+ 
	                				  (partner.state_id ?  partner.state_id[1] : '');

					if(partner.active){
						this.partner_search_string += this._partner_search_string(partner);
					}
	            }
	        }
	        return updated_count;
	    },

		search_partner: function(query){
	        try {
	            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
	            query = query.replace(/ /g,'.+');
	            var re = RegExp("([0-9]+):.*?"+utils.unaccent(query),"gi");
	        }catch(e){
	            return [];
	        }
	        var results = [];
	        for(var i = 0; i < 5; i++){
	            var r = re.exec(utils.unaccent(this.partner_search_string));
	            if(r){
	                var id = Number(r[1]);
	                results.push(this.get_partner_by_id(id));
	            }else{
	                break;
	            }
	        }
	        return results;
	    },
    });
});