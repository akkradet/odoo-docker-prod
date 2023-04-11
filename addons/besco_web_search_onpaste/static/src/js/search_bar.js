odoo.define('besco_web_search_onpaste.SearchBar', function (require) {
    "use strict";

    var SearchBar = require('web.SearchBar');

    return SearchBar.include({
        events: _.extend({}, SearchBar.prototype.events, {
            'paste .o_searchview_input': '_onPasteInput',
        }),
        _onPasteInput: function (e) {
            let input = this.$input
            getPasteValue(e, input, setPasteInputValue);
        }
    })
});