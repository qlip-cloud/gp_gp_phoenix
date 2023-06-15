// Copyright (c) 2021, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_GP_MasterSetup', {

	refresh: function(frm) {

		if (!(frm.is_new())){


				frm.add_custom_button(__('Articulos'), function(){
					if (!frm.is_dirty()){
						sync_item(frm, frm.doc.name)
					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}
					
				});

				frm.add_custom_button(__('Clientes'), function(){
					if (!frm.is_dirty()){

						sync_customer(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});

				frm.add_custom_button(__('Niveles'), function(){
					if (!frm.is_dirty()){

						sync_level(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});

				frm.add_custom_button(__('Transportador'), function(){
					if (!frm.is_dirty()){

						sync_conveyor(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});

				frm.add_custom_button(__('Shipping'), function(){
					if (!frm.is_dirty()){

						sync_shipping_method(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});

				frm.add_custom_button(__('Attributes'), function(){
					if (!frm.is_dirty()){

						sync_attributes_method(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});

				frm.add_custom_button(__('Class'), function(){
					if (!frm.is_dirty()){

						sync_class_method(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});
				frm.add_custom_button(__('Description'), function(){
					if (!frm.is_dirty()){

						sync_description_method(frm, frm.doc.name)

					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}				
				});
			
		}
	},

	onload: function(frm) {
		frm.trigger('execute_sync');

	},

	company: function(frm) {
        frm.trigger('execute_sync');
    },

	execute_sync: function(frm){

		frm.set_query('store_secundary', () => {
			return {
				filters: {
					is_deleted: 0
				}
			}
		})
		
		if (frm.doc.company){

			frappe.call({
				method: 'gp_phonix_integration.gp_phonix_integration.use_case.master_setup.get_master_list',
				args: {
					'company': frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						const resonse = r.message
						console.log(resonse.stores)
						sync_select_option(frm, "store_main", resonse.stores)
						sync_select_option(frm, "price_level", resonse.prices_levels)
						sync_select_option(frm, "order_id", resonse.orders_ids)
						sync_select_option(frm, "customer_class",resonse.customers_class)
					}
				},
				freeze:true
			});
		}
	}
});

function sync_level(frm, master_name){
	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.level_setup.sync_level',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message
				let message = ""
				
				if (response.is_sync){

					message = `
						<ul>
							<li> Total de Niveles:${response.total}</li>  
							<li> Niveles Nuevos: ${response.count_created}</li>
							<li> Niveles actualizados: ${response.count_updated}</li>
							<li> Grupos creados: ${response.count_group_created}</li>
							
						</ul>`
				}
				else{
					message = "No hay niveles en esta configuracion"
				}
				
				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}

function sync_item(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.item_setup.sync_item',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {
				let message = ""

				const response = r.message
				
				if (response.has_pending){
					message = `Existe una sincronización en proceso`

				}
				else{

					message = `Esta sincronización se ejecuta en segundo plano, para mas informacion consulte el Item Sync Log : ${response.item_sync_log_name}`
				}
				
				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}

function sync_customer(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.customer_setup.sync_customer',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message
				let message = ""

				if (response.is_sync){

					message = `
						<ul>
							<li> Total de Clientes:${response.customer_total}</li>  
							<li> clientes Nuevos: ${response.customer_new}</li>
							<li> clientes Agregados: ${response.customer_add}</li>
							<li> clientes Repetidos: ${response.customer_repeat}</li>
							<li> clientes Erroneos: ${response.customer_invalid}</li>
							<li> Grupos de Clientes Agregados: ${response.customer_group_add}</li>
					
						</ul>`
				}
				else{
					message = "No hay Clientes en esta configuracion"
				}
				
				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}
/*function enabled_disabled_control(frm, select_name, status){

//	frm.set_df_property(select_name, "disabled", status);

}*/

function sync_select_option(frm, select_name, format_list){

	frm.set_df_property(select_name, "options", format_list);

}

function sync_conveyor(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.conveyor_setup.sync_conveyor',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message

				const message = `
					<ul>
						<li> Conveyor Total:${response.total_conveyor}</li>
						<li> Conveyor added: ${response.count_conveyor_add}</li>
						<li> Conveyor updated: ${response.count_conveyor_update}</li>
					</ul>`

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}

function sync_shipping_method(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.shipping_method_setup.sync_shipping_method',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message

				const message = `
					<ul>
						<li> Total Items:${response.total_items}</li>
						<li> Customer updated: ${response.count_cust_upd}</li>
						<li> Message Error: ${response.mess_error}</li>
					</ul>`

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}



function sync_attributes_method(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.attributes_setup.sync_attributes',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message
				
				const message = `
					<ul>
						<li> Synchronized Data</li>
					</ul>`

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}

function sync_description_method(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.item_description_setup.sync',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message
				
				let message = ""
				
				if (response.has_pending){
					message = `Existe una sincronización en proceso`

				}
				else{

					message = `Esta sincronización se ejecuta en segundo plano, para mas informacion consulte el Item Sync Description Log : ${response.item_sync_description_log_name}`
				}

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}
function sync_class_method(frm, master_name){

	frappe.call({
		method: 'gp_phonix_integration.gp_phonix_integration.use_case.class_setup.sync_class',
		args: {
			'master_name': master_name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message
				
				const message = `
					<ul>
						<li> Synchronized Data</li>
					</ul>`

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});
			}
		},
		freeze:true

	});
}
