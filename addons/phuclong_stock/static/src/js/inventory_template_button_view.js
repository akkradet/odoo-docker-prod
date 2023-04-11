odoo.define('phuclong_stock.InventoryTemplateView', function (require) {
"use strict";

var InventoryTemplateController = require('phuclong_stock.InventoryTemplateController');
var InventoryUpdateController = require('phuclong_stock.InventoryUpdateController');
var ListView = require('web.ListView');
var PivotView = require('web.PivotView');
var viewRegistry = require('web.view_registry');
var relational_fields = require('web.relational_fields');
var FieldX2Many = relational_fields.FieldX2Many;

var dom = require('web.dom');

var InventoryTemplateView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: InventoryTemplateController
    })
});

viewRegistry.add('inventory_template_button', InventoryTemplateView);

var InventoryUpdateView = PivotView.extend({
    config: _.extend({}, PivotView.prototype.config, {
        Controller: InventoryUpdateController
    })
});

viewRegistry.add('inventory_update_button', InventoryUpdateView);

FieldX2Many.include({
	_render: function () {
        var self = this;
        if (!this.view) {
            return this._super();
        }
        if (this.renderer) {
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            return this.renderer.updateState(this.value, {
                columnInvisibleFields: this.currentColInvisibleFields,
                keepWidths: true,
            }).then(function () {
                self.pager.updateState({ size: self.value.count });
            });
        }
        var arch = this.view.arch;
        var viewType;
        var rendererParams = {
            arch: arch,
        };

        if (arch.tag === 'tree') {
			var check_stockmove_delete = false;
			if(this.model == 'stock.picking' && this.name == 'move_line_ids' && this.recordData.state == 'draft' &&
				this.recordData.picking_type_code == 'internal' && this.recordData.picking_type_operation == 'move'){
				check_stockmove_delete = true;
			}
            viewType = 'list';
            this.currentColInvisibleFields = this._evalColumnInvisibleFields();
            _.extend(rendererParams, {
                editable: this.mode === 'edit' && arch.attrs.editable,
                addCreateLine: !this.isReadonly && this.activeActions.create,
                addTrashIcon: !this.isReadonly && (this.activeActions.delete || check_stockmove_delete),
                isMany2Many: this.isMany2Many,
                columnInvisibleFields: this.currentColInvisibleFields,
            });
        }

        if (arch.tag === 'kanban') {
            viewType = 'kanban';
            var record_options = {
                editable: false,
                deletable: false,
                read_only_mode: this.isReadonly,
            };
            _.extend(rendererParams, {
                record_options: record_options,
                readOnlyMode: this.isReadonly,
            });
        }

        _.extend(rendererParams, {
            viewType: viewType,
        });
        var Renderer = this._getRenderer();
        this.renderer = new Renderer(this, this.value, rendererParams);

        this.$el.addClass('o_field_x2many o_field_x2many_' + viewType);
        if (this.renderer) {
            return this.renderer.appendTo(document.createDocumentFragment()).then(function () {
                dom.append(self.$el, self.renderer.$el, {
                    in_DOM: self.isInDOM,
                    callbacks: [{widget: self.renderer}],
                });
            });
        } else {
            return this._super();
        }
    },
})

});
