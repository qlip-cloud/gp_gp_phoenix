from certifi import contents
import frappe
from erpnext.setup.utils import insert_record
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import ITEM
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.service.command_sql import update_sql, search_new_and_duplicate, list_converter, select_custom_sql, insert, search_new, tuple_format, get_list_common, add_and_format_field, insert_sql
from datetime import datetime
from frappe.utils import now

ITEM_PRICE = "Price"

CURRENCIES_FILEDS = {
    "COP": ITEM_PRICE,
    "EUR": "PriceEU",
    "USD": "PriceUSD"
}
ITEM_NAME = "IdItem"
UOM_NAME = "BaseUnit"
ITEM_GROUP_NAME = "Warehouse"
UOM_BASE = "INQT"
ITEM_HEADER = "ItemsInfo"
ITEM_DESCRIPTION = "Description"
ITEM_MULCANT = "MulCant"
ITEM_SKU="Sku"
ITEM_CLASS="Class"
ITEM_FULL_DESCRIPTION="FullDescription"
ITEM_PRICE_GROUP="PriceGroup"
SHORT_DESCRIPTION="ShortDescription"

ITEM_PRICE_TABLE = "`tabItem Price`"
ITEM_TABLE = "tabItem"
UOM_TABLE = "tabUOM"
ITEM_GROUP_TABLE = "`tabItem Group`"
#ITEM_ATTRIBUTES_TABLE = "tabqp_ItemAttribute"

ITEM_FIELDS = ["name", "item_code", "item_name", "is_stock_item", "disabled", "item_group", "stock_uom", "sku", "qp_phonix_class", "qp_description_full", "qp_price_group", "qp_phoenix_shortdescription"]
UOM_FIELDS = ["name", "uom_name"]
#ITEM_ATTRIBUTES_FIELDS = ["name", "parent", "parentfield", "parenttype", "attribute", "code", "value"]
ITEM_PRICE_FILEDS = ["name", "item_code", "item_name", "item_description", "price_list", "price_list_rate", "valid_from"]

ITEM_ATTRIBUTE_REFERENCE = "item_attributes"
ITEM_DOCTYPE = "Item"
UOM_DOCTYPE = "uoms"

UOM_CONVERTION_FIELDS = ["name", "parent", "parentfield", "parenttype", "uom", "conversion_factor"]
UOM_CONVERTION_TABLE = "`tabUOM Conversion Detail`"

ITEM_SYNC_LINE = ["name", "id_item", "description", "short_description", "generic_description", "full_description", "quantity", "price", "price_eu", "price_usd", "weight", "base_unit", "warehouse", "mulcant", "item_type", "class", "sku", "price_group", "parent", "parentfield", 'parenttype']

ITEM_SYNC_LINETABLE = "tabqp_GP_ItemSyncLines"

@frappe.whitelist()
def sync_item(master_name, store_main = None):

    #if not exist_item_sync_log_pending():
    if True:

        items_response, list_prices, is_price_list_new = get_items(master_name)   
        #items_response, price_list, is_price_list_new = [1,2,3], 123, True

        if items_response:

            item_sync_log = create_item_sync_log()
            async_item(items_response = items_response,
                list_prices =list_prices,
                is_price_list_new = is_price_list_new,
                store_main = store_main,
                master_name = master_name,
                item_sync_log = item_sync_log)
            #frappe.enqueue(
            #    async_item,
            #    queue='long',                
            #    #is_async=True,
            #    now=True,
            #    job_name="Item Sync Log",
            #    timeout=5400000,
            #    items_response = items_response,
            #    list_prices =list_prices,
            #    is_price_list_new = is_price_list_new,
            #    store_main = store_main,
            #    master_name = master_name,
            #    item_sync_log = item_sync_log
            #    )
            
        return {
            "item_sync_log_name": item_sync_log.name,
            "has_pending": False
        }

    return {
            "item_sync_log_name": None,
            "has_pending": True
        }

def exist_item_sync_log_pending():

    #return False
    return frappe.db.exists("qp_GP_ItemSyncLog", {
        "is_complete" : False
    })


def create_item_sync_log():

    item_sync_log = frappe.new_doc("qp_GP_ItemSyncLog")

    item_sync_log.insert()

    return item_sync_log

def async_item(items_response, list_prices, is_price_list_new, store_main, master_name, item_sync_log):
    
    frappe.db.sql("DELETE FROM `tabqp_GP_ItemSyncLines`")
    
    count_items = insert_lines(items_response)
    
    uom_add = insert_UOM()
    
    item_updated = update_items()

    item_add = insert_items()
   
    update_item_sync_log(item_sync_log, True, count_items, uom_add, item_add, item_updated)
    
    frappe.db.commit()
    
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
        
        
def update_items():

    sql = f"""
    UPDATE tabItem AS item
    INNER JOIN tabqp_GP_ItemSyncLines AS line ON item.name = line.name
    SET 
        item.item_code                  = line.id_item,
        item.item_name                  = line.description,
        item.item_group                 = line.warehouse,
        item.qp_phonix_class            = line.class,
        item.qp_description_full        = line.full_description,
        item.qp_price_group             = line.price_group,
        item.qp_phoenix_shortdescription = line.short_description,
        item.modified                   = line.modified
    WHERE NOT (
        item.item_code                  <=> line.id_item AND
        item.item_name                  <=> line.description AND
        item.item_group                 <=> line.warehouse AND
        item.stock_uom                  <=> line.base_unit AND
        item.qp_phonix_class            <=> line.class AND
        item.qp_description_full        <=> line.full_description AND
        item.qp_price_group             <=> line.price_group AND
        item.qp_phoenix_shortdescription <=> line.short_description
    )"""
    
    frappe.db.sql(sql)
    
    return get_count_row()
    
def get_count_row():
    
    result = frappe.db.sql("""SELECT ROW_COUNT() AS count_rows;""", as_dict = 1)
    
    return result[0].get("count_rows", 0)

def insert_items():
    
    sql = f"""
        INSERT INTO tabItem (
            name, 
            item_code, 
            item_name, 
            item_group, 
            stock_uom, 
            sku, 
            qp_phonix_class, 
            qp_description_full, 
            qp_price_group, 
            qp_phoenix_shortdescription, 
            modified,
            creation,
            modified_by,
            owner,
            is_stock_item,
            disabled
        )
        SELECT 
            line.name, 
            line.id_item, 
            line.description, 
            line.warehouse, 
            IFNULL(NULLIF(line.base_unit, ''), '{UOM_BASE}'),          
            'NO', 
            line.class, 
            line.full_description, 
            line.price_group, 
            line.short_description, 
            line.modified,
            NOW(),
            'Administrator',
            'Administrator',
            0,
            0
        FROM tabqp_GP_ItemSyncLines AS line
        LEFT JOIN tabItem AS item ON line.name = item.name
        WHERE item.name IS NULL"""
    
    frappe.db.sql(sql)
    
    return get_count_row()

def insert_UOM():
    
    sql = """
        INSERT INTO tabUOM (
            name, 
            uom_name,
            modified,
            creation,
            modified_by,
            owner
        )
        SELECT 
            line.base_unit, 
            line.base_unit, 
            NOW(),
            NOW(),
            'Administrator',
            'Administrator'
            
        FROM tabqp_GP_ItemSyncLines AS line
        LEFT JOIN tabUOM AS uom ON line.base_unit = uom.name
        WHERE 
            uom.name IS NULL 
            AND line.base_unit IS NOT NULL 
            AND line.base_unit <> ''
        GROUP BY line.base_unit"""
    
    frappe.db.sql(sql)
    
    return get_count_row()
    
def update_item_sync_log(item_sync_log, is_sync, count_items = 0, uom_add = 0, item_add = 0, item_updated = 0, item_price_update = 0, is_price_list_new = 0):

    item_sync_log.count_items = count_items
    item_sync_log.item_duplicate = count_items - item_add
    item_sync_log.item_add = item_add
    item_sync_log.item_updated = item_updated
    item_sync_log.uom_add = uom_add
    item_sync_log.item_price_add = item_add
    item_sync_log.item_price_update = item_price_update
    item_sync_log.is_price_list_new = is_price_list_new
    item_sync_log.is_sync = is_sync
    item_sync_log.is_complete = True
    item_sync_log.sync_finish = now()

    item_sync_log.save()

def set_note_sync(response, store_main, master_name):

    new_note = frappe.get_doc({
        "doctype": "Note", 
        "title" : "Sync auto {} {} master_setup id: {}".format(now(), store_main, master_name),
        "content": json.dumps(response)
        })

    new_note.insert()

def get_sync_response(is_sync, items_response = None, count_repeat = None, item_add = None, item_price_update = None, is_price_list_new = None):
    
    response = {
            "is_sync": is_sync
        }

    if is_sync:
        
        response.update({
            "count_items": len(items_response),
            "item_duplicate": count_repeat,
            "item_add": item_add,
            "item_price_add": item_add,
            "item_price_update": item_price_update,
            "is_price_list_new": is_price_list_new
        })

    return response
    

def get_items(master_name):

    company, price_level, store_id_main, store_id_secundary = __get_basic_params(master_name)

    list_prices, is_price_list_new = __find_or_create_price_list(price_level, company)
    
    store_list = __get_store_list(store_id_main, store_id_secundary)
    
    item_response =  __search_items(price_level, store_list, company)
    
    return item_response.get(ITEM_HEADER), list_prices, is_price_list_new

    
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

def __get_store_list(store_id_main, store_id_secundary):

    store_list = [__create_store_object(store_id_main)]

    list_secundary = list(map(lambda x: __create_store_object(x), store_id_secundary))

    #return store_list + list_secundary
    return store_list 

def __create_store_object(store_id):

    return {
        "Id": store_id
    }

def __get_basic_params(master_name):

    master_setup = get_master_setup(master_name)

    store_id_main = master_setup.get_store_id_main()

    store_id_secundary = master_setup.get_store_id_secundary()

    return master_setup.company, master_setup.price_level, store_id_main, store_id_secundary

def __find_or_create_price_list(price_level, company_name):

    list_prices_setup = get_list_prices_setup(price_level)
    
    list_prices = []

    count = 0

    for list_price_setup in list_prices_setup:

        if not frappe.db.exists("Price List", list_price_setup.get("name")):

            price_list = frappe.new_doc("Price List")

            price_list.price_list_name = list_price_setup.get("name")
            price_list.currency = list_price_setup.get("currency")
            price_list.selling = True
            price_list.enabled = True
            price_list.save()
            count += 1

        else:

            price_list = frappe.get_doc("Price List", list_price_setup.get("name"))

        list_prices.append(price_list)

    return list_prices, count

def get_list_prices_setup(price_level):

    currencies = ["COP", "USD", "EUR"]
    
    list_prices_setup = []
    
    for currency in currencies:

        price_level_name = price_level

        if currency != "COP":
        
            price_level_name += " " + currency
        
        list_prices_setup.append({
            "name": price_level_name,
            "currency": currency
        })

    return list_prices_setup