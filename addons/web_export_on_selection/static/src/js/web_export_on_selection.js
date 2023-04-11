odoo.define('web_export_on_selection.web_export_on_selection', function (require) {
"use strict";

var DataExport = require('web.DataExport');

DataExport.include({
	
	init: function (parent, record, defaultExportFields, groupedBy, activeDomain, idsToExport) {
        this._super(parent, record, defaultExportFields, groupedBy, activeDomain, idsToExport);
        this.idsToExport = idsToExport;
    },
    
    export() {
        let exportedFields = this.defaultExportFields.map(field => ({
            name: field,
            label: this.record.fields[field].string,
        }));
        this._exportData(exportedFields, 'xlsx', this.idsToExport);
    },
    
});

});
