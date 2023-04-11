odoo.define('besco_web_search_onpaste.search_filters', function (require) {
    "use strict";

    var search_filters = require('web.search_filters');

    return search_filters.ExtendedSearchProposition.include({
        events: _.extend({}, search_filters.ExtendedSearchProposition.prototype.events, {
            'paste .o_searchview_extended_prop_value input': '_onPasteInput',
        }),
        _onPasteInput: function (e) {
            let input = this.value.$el
            getPasteValue(e, input, setPasteInputValue);
        }
    })
});