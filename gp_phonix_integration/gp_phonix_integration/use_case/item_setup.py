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

ITEM_NAME = "IdItem"
UOM_NAME = "BaseUnit"
ITEM_GROUP_NAME = "Warehouse"
UOM_BASE = "INQT"
ITEM_PRICE = "Price"
ITEM_HEADER = "ItemsInfo"
ITEM_DESCRIPTION = "Description"
ITEM_MULCANT = "MulCant"
ITEM_SKU="Sku"
ITEM_CLASS="Class"
ITEM_FULL_DESCRIPTION="FullDescription"
ITEM_PRICE_GROUP="PriceGroup"

ITEM_PRICE_TABLE = "`tabItem Price`"
ITEM_TABLE = "tabItem"
UOM_TABLE = "tabUOM"
ITEM_GROUP_TABLE = "`tabItem Group`"
ITEM_ATTRIBUTES_TABLE = "tabqp_ItemAttribute"

ITEM_FIELDS = ["name", "item_code", "item_name", "is_stock_item", "disabled", "item_group", "stock_uom", "sku", "qp_phonix_class", "qp_description_full", "qp_price_group"]
UOM_FIELDS = ["name", "uom_name"]
ITEM_ATTRIBUTES_FIELDS = ["name", "parent", "parentfield", "parenttype", "attribute", "code", "value"]
ITEM_PRICE_FILEDS = ["name", "item_code", "item_name", "item_description", "price_list", "price_list_rate", "valid_from"]

ITEM_ATTRIBUTE_REFERENCE = "item_attributes"
ITEM_DOCTYPE = "Item"
UOM_DOCTYPE = "uoms"

UOM_CONVERTION_FIELDS = ["name", "parent", "parentfield", "parenttype", "uom", "conversion_factor"]
UOM_CONVERTION_TABLE = "`tabUOM Conversion Detail`"


@frappe.whitelist()
def sync_item(master_name, store_main = None):

    if not exist_item_sync_log_pending():
    #if True:

        items_response, price_list, is_price_list_new = get_items(master_name)   
        #items_response, price_list, is_price_list_new = [1,2,3], 123, True

        if items_response:

            item_sync_log = create_item_sync_log()

            frappe.enqueue(
                async_item,
                queue='long',                
                is_async=True,
                job_name="Item Sync Log",
                timeout=5400000,
                items_response = items_response,
                price_list =price_list,
                is_price_list_new = is_price_list_new,
                store_main = store_main,
                master_name = master_name,
                item_sync_log = item_sync_log
                )
            
        return {
            "item_sync_log_name": item_sync_log.name,
            "has_pending": False
        }

    return {
            "item_sync_log_name": None,
            "has_pending": True
        }

def exist_item_sync_log_pending():

    return frappe.db.exists("qp_GP_ItemSyncLog", {
        "is_complete" : False
    })

def create_item_sync_log():

    item_sync_log = frappe.new_doc("qp_GP_ItemSyncLog")

    item_sync_log.insert()

    return item_sync_log

def async_item(items_response, price_list, is_price_list_new, store_main,
               master_name, item_sync_log):
        
        uom_save(items_response)

        item_group_save(items_response)

        UOM_LIST = frappe.db.get_list('UOM', pluck='name')
        
        item_add, count_repeat, item_price_update = item_save(items_response, price_list, UOM_LIST)

        #response = get_sync_response(True, items_response, count_repeat, item_add, item_price_update, is_price_list_new)

        #if store_main:

            #set_note_sync(response, store_main, master_name)
        
        update_item_sync_log(item_sync_log, True, items_response, count_repeat, item_add, item_price_update, is_price_list_new)
        
        frappe.db.commit()

        #return response

def update_item_sync_log(item_sync_log, is_sync, items_response = None, count_repeat = None, item_add = None, item_price_update = None, is_price_list_new = None):

    item_sync_log.count_items = len(items_response)
    item_sync_log.item_duplicate = count_repeat
    item_sync_log.item_add = item_add
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
    

def item_save(items_response, price_list, uom_list):

    item_price_script = []

    count_update = 0

    item_new, count_repeat, list_repeat, count_whitespace = search_new_and_duplicate(items_response, ITEM_NAME, ITEM_TABLE)

    if item_new:
        
        item_script, item_attribute_script, item_price_script, item_uoms_script = filter_item(item_new, items_response, price_list, uom_list)

        insert(item_script, ITEM_FIELDS, ITEM_TABLE)

        insert(item_price_script, ITEM_PRICE_FILEDS, ITEM_PRICE_TABLE)

        #insert(item_attribute_script, ITEM_ATTRIBUTES_FIELDS, ITEM_ATTRIBUTES_TABLE)

        insert(item_uoms_script, UOM_CONVERTION_FIELDS, UOM_CONVERTION_TABLE)

    if list_repeat:
        
        count_update = filter_item_price_update(items_response, list_repeat, price_list)

    return len(item_new), count_repeat, count_update

def filter_item_price_update(items_response, list_repeat, price_list):

    count = 0

    price_list_name = price_list.name

    search = "name, item_code, price_list_rate"

    condition = "price_list = '{}' and item_code in {}".format(price_list_name, list_converter(list_repeat))

    list_result = select_custom_sql(search, ITEM_PRICE_TABLE, condition)

    for item_price in list_result:

        item = [item for item in items_response if item.get(ITEM_NAME) == item_price[1]]

        if item:

            price = item[0].get(ITEM_PRICE)

            if  float(price) != float(item_price[2]):

                set_expresion = "price_list_rate = {}".format(price)
                
                where_codition = "name = '{}'".format(item_price[0])
                
                update_sql(ITEM_PRICE_TABLE, set_expresion, where_codition)

                count +=1

    return count

def item_group_save(items_response):

    item_group_new, count_repeat, count_whitespace = search_new(items_response, ITEM_GROUP_NAME, ITEM_GROUP_TABLE)
    
    list(map(lambda item_group: __sync_item_group(item_group), item_group_new))

def uom_save(items_response):

    uom_new, count_repeat, count_whitespace = search_new(items_response, UOM_NAME, UOM_TABLE, add_default = [UOM_BASE], is_id_upper = True)

    if uom_new:
    
        uom_script, count = preparate_uom(uom_new)

        insert(uom_script, UOM_FIELDS, UOM_TABLE)

    return uom_new

def preparate_uom(list_new):
    
    list_script = []

    count_add = 0

    for new in list_new:

        if new and new != "":
            
            script = []

            script.append(new)
            
            script.append(new)
            
            script += get_list_common()

            list_script.append(tuple(script))

            count_add+=1

    return tuple_format(list_script), count_add

def get_items(master_name):

    company, price_level, store_id_main, store_id_secundary = __get_basic_params(master_name)

    price_list, is_price_list_new = __find_or_create_price_list(price_level, company)
    
    store_list = __get_store_list(store_id_main, store_id_secundary)
    
    item_response =  __search_items(price_level, store_list, company)
    
    return item_response.get(ITEM_HEADER), price_list, is_price_list_new

    
    #return get_mock_items(), price_list, is_price_list_new

def __search_items(price_level, store_list, company):

    json_data = json.dumps({
        "PriceLevel": price_level,
        "Warehouses": store_list
    })

    return execute_send(company_name = company, endpoint_code = ITEM, json_data = json_data)

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

    company = frappe.get_doc("Company", company_name)

    if not frappe.db.exists("Price List", price_level):

        price_list = frappe.new_doc("Price List")

        price_list.price_list_name = price_level
        price_list.currency = company.default_currency
        price_list.selling = True
        price_list.enabled = True
        price_list.save()

        return price_list, 1

    else:

        return frappe.get_doc("Price List", price_level), 0

def __sync_item_group(gp_item_group):

    if gp_item_group and not frappe.db.exists("Item Group", gp_item_group):

        records = [
            {
                'doctype': 'Item Group', 
                'item_group_name': frappe._(gp_item_group),
                'is_group': 0, 
                'parent_item_group': frappe._('All Item Groups')
            }
        ]

        insert_record(records)

    return gp_item_group

def filter_item(list_new, list_items, price_list, uom_list):
    
    list_item_script = []

    list_item_price_script = []

    list_item_attribute_script = []

    list_item_price_script = []

    list_uoms_script = []
    
    item_group = frappe.get_doc("Item Group","Productos")

    for new in list_new:
        
        item_filter = list(filter(lambda item: item.get(ITEM_NAME) == new, list_items))

        if item_filter:

            script_items = preparate_item(item_filter[0], item_group.name, uom_list)

            list_item_script.append(script_items)

            script_item_price = preparate_item_price(item_filter[0], price_list)

            list_item_price_script.append(script_item_price)

            script_uoms = preparate_uom_conversion(item_filter[0], uom_list=uom_list)

            list_uoms_script.append(script_uoms)

            script_uoms = preparate_uom_conversion(item_filter[0], take_base = True, uom_list=uom_list)

            list_uoms_script.append(script_uoms)

            if item_filter[0].get("Categoria") !="" and item_filter[0].get("DescCat") != "":

                script_items_attributes = preparate_item_attributes(item_filter[0].get(ITEM_NAME), 'Categoria', item_filter[0].get("Categoria"), item_filter[0].get("DescCat"))
            
                list_item_attribute_script.append(script_items_attributes)
                
            if item_filter[0].get("SubCategoria") != "" and item_filter[0].get("DescSubCat")!= "":
            
                script_items_attributes = preparate_item_attributes(item_filter[0].get(ITEM_NAME), 'SubCategoria', item_filter[0].get("SubCategoria"), item_filter[0].get("DescSubCat"))

                list_item_attribute_script.append(script_items_attributes)

    return tuple_format(list_item_script), tuple_format(list_item_attribute_script), tuple_format(list_item_price_script), tuple_format(list_uoms_script)


def preparate_uom_conversion(item, take_base = False, uom_list = []):

    script = []

    item_code = item.get(ITEM_NAME)

    uom_unit = __doc_uom(item.get(UOM_NAME), uom_list)

    uom_id = UOM_BASE if not take_base else uom_unit

    name = "{}:{}".format(item_code, uom_id)

    mul_cant = item.get(ITEM_MULCANT) if item.get(ITEM_MULCANT) and not take_base else 1

    script.append(name)
    script.append(item_code)
    script.append(UOM_DOCTYPE)
    script.append(ITEM_DOCTYPE)
    script.append(uom_id)
    script.append(mul_cant)

    script += get_list_common()

    return tuple(script)

def preparate_item_price(item, price_list):

    script = []

    item_code = item.get(ITEM_NAME)

    item_name = item.get(ITEM_DESCRIPTION)

    name = "{}:{}".format(item_code, price_list.name)

    script.append(name)

    script.append(item_code)
    
    script.append(item_name)

    script.append(item_name)

    script.append(price_list.name)

    script.append(item.get(ITEM_PRICE))

    script.append(frappe.utils.today())

    script += get_list_common()

    return tuple(script)


def preparate_item_attributes(item_name, attribute, code, value):

    script = []

    name = "{}:{}".format(item_name, attribute)

    script.append(name)

    script.append(item_name)
    
    script.append(ITEM_ATTRIBUTE_REFERENCE)

    script.append(ITEM_DOCTYPE)

    script.append(attribute)

    script.append(code)

    script.append(value)

    script += get_list_common()

    return tuple(script)

def preparate_item(new, item_group, uom_list):
    #print(new.get(ITEM_NAME))
    uom_unit = __doc_uom(new.get(UOM_NAME), uom_list)
    
    script = []

    script.append(new.get(ITEM_NAME))

    script.append(new.get(ITEM_NAME))
    
    script.append(new.get(ITEM_DESCRIPTION))

    script.append(False)

    script.append(True)

    script.append(new.get(ITEM_GROUP_NAME) or item_group)

    script.append(uom_unit)
    #ACIEGAS
    script.append(new.get(ITEM_SKU))
    
    script.append(new.get(ITEM_CLASS))

    script.append(new.get(ITEM_FULL_DESCRIPTION))

    script.append(new.get(ITEM_PRICE_GROUP))
    
    script += get_list_common()

    return tuple(script)

def __doc_uom(UndBase, uom_list = None):

    uom_unit = UOM_BASE

    if UndBase:

        #doc_uom = frappe.get_doc('UOM', UndBase.upper())

        #uom_unit = doc_uom.name # Para unidades de medidas existentes que no están en mayúsculas

        search = list(filter(lambda iter_uom: iter_uom == UndBase.upper(), uom_list))

        uom_unit = search[0]

    return uom_unit