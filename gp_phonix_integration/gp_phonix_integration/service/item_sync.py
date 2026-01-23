import frappe
from gp_phonix_integration.gp_phonix_integration.service.command_sql import insert, tuple_format, get_list_common
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import ITEM
from datetime import datetime
from frappe.utils import now
import json

ITEM_SYNC_LINE = ["name", "id_item", "description", "short_description", "generic_description", "full_description", "quantity", "price", "price_eu", "price_usd", "weight", "base_unit", "warehouse", "mulcant", "item_type", "class", "sku", "price_group", "parent", "parentfield", 'parenttype']

ITEM_SYNC_LINETABLE = "tabqp_GP_ItemSyncLines"

ITEM_HEADER = "ItemsInfo"

def exist_item_sync_log_pending():

    return frappe.db.exists("qp_GP_ItemSyncLog", {
        "is_complete" : False
    })
    
def create_item_sync_log():

    item_sync_log = frappe.new_doc("qp_GP_ItemSyncLog")

    item_sync_log.insert()

    return item_sync_log

def execute_sync_items(items_response):
    
    frappe.db.sql("DELETE FROM `tabqp_GP_ItemSyncLines`")
    
    return insert_lines(items_response)
    
def insert_lines(items_response):
    
    batch_size = 1000
    
    for i in range(0, len(items_response), batch_size):
        
        list_item_script = []
        
        batch = items_response[i:i + batch_size]
        
        for new in batch:
            
            base_unit = new.get("BaseUnit").upper()
            
            script = []

            script.append(new.get("IdItem"))
            script.append(new.get("IdItem"))
            script.append(new.get("Description"))
            script.append(new.get("ShortDescription"))
            script.append(new.get("GenericDescription"))
            script.append(new.get("FullDescription"))
            script.append(new.get("Quantity"))
            script.append(new.get("Price"))
            script.append(new.get("PriceEU"))
            script.append(new.get("PriceUSD"))
            script.append(new.get("Weight"))
            script.append(base_unit)
            script.append(new.get("Warehouse"))
            script.append(new.get("MulCant"))
            script.append(new.get("ItemType"))
            script.append(new.get("Class"))
            script.append(new.get("Sku"))
            script.append(new.get("PriceGroup"))
            script.append("qp_GP_ItemSync")
            script.append("lines")
            script.append("qp_GP_ItemSync")

            script += get_list_common()

            list_item_script.append(tuple(script))
        
        item_script = tuple_format(list_item_script)
        
        insert(item_script, ITEM_SYNC_LINE, ITEM_SYNC_LINETABLE)
        
    return frappe.db.count('qp_GP_ItemSyncLines')

def get_count_row():
    
    result = frappe.db.sql("""SELECT ROW_COUNT() AS count_rows;""", as_dict = 1)
    
    return result[0].get("count_rows", 0)

def update_item_sync_log(item_sync_log, count_items = None, count_insert_UOM = None, count_insert_item_group = None, count_update_items = None, count_insert_items = None, count_insert_uom_convertion = None, count_price_list_add = None, count_price_item_add = None, count_price_item_update = None, is_sync = True):

    item_sync_log.count_items = count_items
    item_sync_log.count_insert_UOM = count_insert_UOM
    item_sync_log.count_insert_item_group = count_insert_item_group
    item_sync_log.count_update_items = count_update_items
    item_sync_log.count_insert_items = count_insert_items
    item_sync_log.count_insert_uom_convertion = count_insert_uom_convertion
    item_sync_log.count_price_list_add = count_price_list_add
    item_sync_log.count_price_item_add = count_price_item_add
    item_sync_log.count_price_item_update = count_price_item_update
    item_sync_log.is_sync = is_sync
    item_sync_log.is_complete = True
    item_sync_log.sync_finish = now()

    item_sync_log.save()
    
def get_items_and_price_list(master_setup):

    item_response = get_items(master_setup)
    
    return item_response, master_setup.price_level

def get_items(master_setup):

    store_list = [{
        "Id": master_setup.get_store_id_main()
    }]
    
    item_response =  __search_items(master_setup.price_level, store_list, master_setup.company)
    
    return item_response.get(ITEM_HEADER)

    #return get_mock_items(), price_list, is_price_list_new, 

def __search_items(price_level, store_list, company):

    json_data = json.dumps({
        "PriceLevel": price_level,
        "Warehouses": store_list
    })

    return execute_send(company_name = company, endpoint_code = ITEM, json_data = json_data)
    
    #with open('/workspace/development/mentum_localhost/apps/gp_phonix_integration/gp_phonix_integration/gp_phonix_integration/use_case/salida.txt', 'r', encoding='utf-8') as file:
    #    contenido = file.read()
    #    
    #return json.loads(contenido)