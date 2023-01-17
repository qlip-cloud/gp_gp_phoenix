from certifi import contents
import frappe
from erpnext.setup.utils import insert_record
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import SYNART
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.service.command_sql import update_sql, search_new_and_duplicate, list_converter, select_custom_sql, insert, search_new, tuple_format, get_list_common, add_and_format_field, insert_sql, search_new_warehouse
from datetime import datetime
from frappe.utils import now

ITEM_NAME = "IdArticulo"
UOM_NAME = "UndBase"
ITEM_GROUP_NAME = "Bodega"
UOM_BASE = "INQT"

ITEM_GROUP_NAME_BALL = "Clase"

WAREHOUSE_TABLE = "`tabWarehouse`"
WAREHOUSE_NAME = "Bodega"

WAREHOUSE_DEFAULT_DOCTYPE = "item_defaults"
WAREHOUSEDEFAULT_FIELDS = ["name", "parent", "parentfield", "parenttype", "company", "default_warehouse", "default_price_list"]
WAREHOUSEDEFAULT_TABLE = "`tabItem Default`"

ITEM_PRICE_TABLE = "`tabItem Price`"
ITEM_TABLE = "tabItem"
UOM_TABLE = "tabUOM"
ITEM_GROUP_TABLE = "`tabItem Group`"
ITEM_ATTRIBUTES_TABLE = "tabqp_ItemAttribute"

ITEM_FIELDS = ["name", "item_code", "item_name", "is_stock_item", "disabled", "item_group", "stock_uom"]
UOM_FIELDS = ["name", "uom_name"]
ITEM_ATTRIBUTES_FIELDS = ["name", "parent", "parentfield", "parenttype", "attribute", "code", "value"]
ITEM_PRICE_FILEDS = ["name", "item_code", "item_name", "item_description", "price_list", "price_list_rate", "valid_from"]

ITEM_ATTRIBUTE_REFERENCE = "item_attributes"
ITEM_DOCTYPE = "Item"
UOM_DOCTYPE = "uoms"

UOM_CONVERTION_FIELDS = ["name", "parent", "parentfield", "parenttype", "uom", "conversion_factor"]
UOM_CONVERTION_TABLE = "`tabUOM Conversion Detail`"


@frappe.whitelist()
def sync_item_ball(master_name, store_main = None):

    items_response, price_list, is_price_list_new = get_items(master_name)

    if items_response:

        # Filtar para omitir registro de articulos con precio en cero

        items_response_orig = items_response

        # Registrar 1 si viene con precio cero float(get("Precio")) or 1 y se notifica cantidad de productos con precios en cero

        items_response_price = [item_dict for item_dict in items_response if float(item_dict.get("Precio")) > 0.00]

        item_price_zero = len(items_response_orig) - len(items_response_price)
    
        uom_save(items_response)

        item_group_save(items_response)

        company_obj = get_company_config(master_name)

        # Guardar Warehouse nuevos si la respuesta tiene incluido el atributo Clase

        warehouse_save(items_response, company_obj)
        
        item_add, count_repeat, item_price_update, insert_item_price, insert_default_item_price = item_save(items_response, price_list, company_obj)

        frappe.db.commit()

        response = get_sync_response(True, items_response, count_repeat, item_add, item_price_update, is_price_list_new, item_price_zero, insert_item_price, insert_default_item_price)

        if store_main:

            set_note_sync(response, store_main, master_name)

        return response

    return get_sync_response(False)

def set_note_sync(response, store_main, master_name):

    new_note = frappe.get_doc({
        "doctype": "Note", 
        "title" : "Sync auto {} {} master_setup id: {}".format(now(), store_main, master_name),
        "content": json.dumps(response)
        })

    new_note.insert()

    frappe.db.commit()


def get_sync_response(is_sync, items_response = None, count_repeat = None, item_add = None, item_price_update = None, is_price_list_new = None, item_price_zero = None, insert_item_price = None, insert_default_item_price = None):
    
    response = {
            "is_sync": False
        }

    if is_sync:
        
        response.update({
            "is_sync": is_sync,
            "count_items": len(items_response),
            "item_duplicate": count_repeat,
            "item_add": item_add,
            "item_price_add": item_add,
            "item_price_update": item_price_update,
            "is_price_list_new": is_price_list_new,
            "item_price_zero": item_price_zero,
            "insert_item_price": insert_item_price,
            "insert_default_item_price": insert_default_item_price
        })

    return response
    

def item_save(items_response, price_list, company_obj):

    item_price_script = []

    count_update = 0
    count_insert_item_price=0
    count_insert_default_item_price = 0
    item_new, count_repeat, list_repeat, count_whitespace = search_new_and_duplicate(items_response, ITEM_NAME, ITEM_TABLE)

    if item_new:
        
        item_script, item_attribute_script, item_price_script, item_uoms_script, items_warehouse_script = filter_item(item_new, items_response, price_list, company_obj)

        insert(item_script, ITEM_FIELDS, ITEM_TABLE)

        insert(item_price_script, ITEM_PRICE_FILEDS, ITEM_PRICE_TABLE)

        if not company_obj.is_the_handling_of_attributes_in_products_optional:

            insert(item_attribute_script, ITEM_ATTRIBUTES_FIELDS, ITEM_ATTRIBUTES_TABLE)

        insert(item_uoms_script, UOM_CONVERTION_FIELDS, UOM_CONVERTION_TABLE)

        if items_warehouse_script:

            insert(items_warehouse_script, WAREHOUSEDEFAULT_FIELDS, WAREHOUSEDEFAULT_TABLE)

    if list_repeat:

        count_update = filter_item_price_update(items_response, list_repeat, price_list, company_obj.name)

        count_insert_item_price = set_item_price_by_company(items_response, list_repeat, price_list)

        count_insert_default_item_price = set_default_warehouse_item_price_by_company(items_response, list_repeat, price_list, company_obj)

        # TODO: Evaluar la actualización de bodega por defecto/lista de precio por defecto por item y compañía

    return len(item_new), count_repeat, count_update, count_insert_item_price, count_insert_default_item_price


def set_item_price_by_company(items_response, list_repeat, price_list):

    # set list price by company by product

    count = 0

    list_item_price_script = []

    # Cosultar si el producto no se encuentra en "price_list - company_abbr" se agrega

    sql_item_add = """
        Select distinct name from tabItem
        Where item_code in {} and item_code not in (
            select item_code from {} where price_list = '{}'
        )
    """.format(list_converter(list_repeat), ITEM_PRICE_TABLE, price_list.name)
    list_result = frappe.db.sql_list(sql_item_add)

    for item_price in list_result:

        item = list(filter(lambda item: item[ITEM_NAME] == item_price, items_response))

        if item:

            script_item_price = preparate_item_price(item[0], price_list)

            list_item_price_script.append(script_item_price)

            count += 1

    list_item_price_script = tuple_format(list_item_price_script)

    if list_item_price_script:
        insert(list_item_price_script, ITEM_PRICE_FILEDS, ITEM_PRICE_TABLE)

    return count


def set_default_warehouse_item_price_by_company(items_response, list_repeat, price_list, company_obj):

    # set default

    count = 0

    list_warehouse_script = []

    # Consulta si la relación item - company del producto no existe se agrega warehouse y list_price
    sql_item_add = """
        Select distinct name from tabItem
        Where item_code in {} and item_code not in (
            select parent from {}
            where parentfield = 'item_defaults' and parenttype = 'Item' and company = '{}'
        )
    """.format(list_converter(list_repeat), WAREHOUSEDEFAULT_TABLE, company_obj.name)
    list_result = frappe.db.sql_list(sql_item_add)

    for item_company in list_result:

        item = list(filter(lambda item: item[ITEM_NAME] == item_company, items_response))

        if item:

            script_warehouse = preparate_warehouse(item[0], company_obj, price_list)

            list_warehouse_script.append(script_warehouse)

            count += 1

    list_warehouse_script = tuple_format(list_warehouse_script)

    if list_warehouse_script:
        insert(list_warehouse_script, WAREHOUSEDEFAULT_FIELDS, WAREHOUSEDEFAULT_TABLE)

    return count


def filter_item_price_update(items_response, list_repeat, price_list, company_name):

    count = 0

    price_list_name = price_list.name

    search = "name, item_code, price_list_rate"

    condition = "price_list = '{}' and item_code in {}".format(price_list_name, list_converter(list_repeat))

    list_result = select_custom_sql(search, ITEM_PRICE_TABLE, condition)

    for item_price in list_result:

        item = [item for item in items_response if item.get(ITEM_NAME) == item_price[1]]

        if item:

            price = __get_price_dict(item[0].get("Precio"))

            if  float(price) != float(item_price[2]):

                set_expresion = "price_list_rate = {}".format(price)
                
                where_codition = "name = '{}'".format(item_price[0])
                
                update_sql(ITEM_PRICE_TABLE, set_expresion, where_codition)

                count +=1

    return count


def item_group_save(items_response):

    # Se incluye Clase en lugar de Bodega en grupo de productos

    if items_response[0].get("Clase"):

        item_group_new, count_repeat, count_whitespace = search_new(items_response, ITEM_GROUP_NAME_BALL, ITEM_GROUP_TABLE)

    else:

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

    return item_response.get("Articulos"), price_list, is_price_list_new

    #return get_mock_items(), price_list, is_price_list_new

def get_company_config(master_name):

    master_setup = get_master_setup(master_name)

    return frappe.get_doc("Company", master_setup.company)

def __search_items(price_level, store_list, company):

    json_data = json.dumps({
        "Lista_Precio": price_level,
        "Bodegas": store_list,
        "compania": company
    })

    return execute_send(company_name = company, endpoint_code = SYNART, json_data = json_data)

def __get_store_list(store_id_main, store_id_secundary):

    store_list = [__create_store_object(store_id_main)]

    list_secundary = list(map(lambda x: __create_store_object(x), store_id_secundary))

    return store_list + list_secundary

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

    # Determinar el name de price_level concatenando con al abreviatura de la compañía
    price_level_ball = "{} - {}".format(price_level, company.abbr)

    if not frappe.db.exists("Price List", price_level_ball):

        price_list = frappe.new_doc("Price List")

        price_list.price_list_name = price_level_ball
        price_list.currency = company.default_currency
        price_list.selling = True
        price_list.enabled = True
        price_list.save()

        return price_list, 1

    else:

        return frappe.get_doc("Price List", price_level_ball), 0

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

def filter_item(list_new, list_items, price_list, company_obj):
    
    list_item_script = []

    list_item_price_script = []

    list_item_attribute_script = []

    list_item_price_script = []

    list_uoms_script = []

    list_warehouse_script = []
    
    item_group = frappe.get_doc("Item Group",frappe._("Products"))

    for new in list_new:
        
        item_filter = list(filter(lambda item: item.get(ITEM_NAME) == new, list_items))

        if item_filter:

            script_items = preparate_item(item_filter[0], item_group.name)

            list_item_script.append(script_items)

            script_item_price = preparate_item_price(item_filter[0], price_list)

            list_item_price_script.append(script_item_price)

            script_uoms = preparate_uom_conversion(item_filter[0])

            list_uoms_script.append(script_uoms)

            script_uoms = preparate_uom_conversion(item_filter[0], take_base = True)

            list_uoms_script.append(script_uoms)

            # Guardar Warehouse si la respuesta tiene incluido el atributo Clase
            if item_filter[0].get("Clase"):

                script_warehouse = preparate_warehouse(item_filter[0], company_obj, price_list)

                list_warehouse_script.append(script_warehouse)

            if item_filter[0].get("Categoria") !="" and item_filter[0].get("DescCat") != "":

                script_items_attributes = preparate_item_attributes(item_filter[0].get(ITEM_NAME), 'Categoria', item_filter[0].get("Categoria"), item_filter[0].get("DescCat"))
            
                list_item_attribute_script.append(script_items_attributes)
                
            if item_filter[0].get("SubCategoria") != "" and item_filter[0].get("DescSubCat")!= "":
            
                script_items_attributes = preparate_item_attributes(item_filter[0].get(ITEM_NAME), 'SubCategoria', item_filter[0].get("SubCategoria"), item_filter[0].get("DescSubCat"))

                list_item_attribute_script.append(script_items_attributes)

    return tuple_format(list_item_script), tuple_format(list_item_attribute_script), tuple_format(list_item_price_script), tuple_format(list_uoms_script), tuple_format(list_warehouse_script)


def preparate_uom_conversion(item, take_base = False):

    script = []

    item_code = item.get(ITEM_NAME)

    uom_unit = __doc_uom(item.get("UndBase"))

    uom_id = UOM_BASE if not take_base else uom_unit

    name = "{}:{}".format(item_code, uom_id)

    mul_cant = item.get("MulCant") if item.get("MulCant") and not take_base else 1




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

    item_name = item.get("Desc_Articulo")

    name = "{}:{}".format(item_code, price_list.name)

    script.append(name)

    script.append(item_code)
    
    script.append(item_name)

    script.append(item_name)

    script.append(price_list.name)

    script.append(__get_price_dict(item.get("Precio")))

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

def preparate_item(new, item_group):

    uom_unit = __doc_uom(new.get("UndBase"))
    
    script = []

    script.append(new.get(ITEM_NAME))

    script.append(new.get(ITEM_NAME))
    
    script.append(new.get("Desc_Articulo"))

    script.append(False)

    script.append(True)

    # Se incluye Clase en lugar de Bodega como grupo de productos

    if new.get("Clase"):

        script.append(new.get("Clase") or item_group)

    else:

        script.append(new.get("Bodega") or item_group)

    script.append(uom_unit)
    
    script += get_list_common()

    return tuple(script)

def __doc_uom(UndBase):

    uom_unit = UOM_BASE

    if UndBase:

        doc_uom = frappe.get_doc('UOM', UndBase.upper())

        uom_unit = doc_uom.name # Para unidades de medidas existentes que no están en mayúsculas

    return uom_unit

def warehouse_save(items_response, company_obj):

    # Si se incluye Clase, se crea Bodega

    if items_response[0].get("Clase"):

        gp_warehouse_new, count_repeat, count_whitespace = search_new_warehouse(items_response, WAREHOUSE_NAME, WAREHOUSE_TABLE, company_obj.abbr)

    else:

        gp_warehouse_new = []

    list(map(lambda gp_warehouse: __sync_warehouse(gp_warehouse, company_obj), gp_warehouse_new))


def __sync_warehouse(gp_warehouse, company_obj):

    if gp_warehouse and not frappe.db.exists("Warehouse", gp_warehouse):

        parent_name = frappe._('All Warehouses')

        company_abbr = company_obj.abbr

        records = [
            {
                'doctype': 'Warehouse',
                'warehouse_name': gp_warehouse.split(' - ')[0],
                'is_group': 0,
                'parent_warehouse': __get_format_warehouse_name(parent_name, company_abbr),
                'company':  company_obj.name
            }
        ]

        insert_record(records)

    return gp_warehouse

def preparate_warehouse(item, company_obj, price_list):

    script = []

    item_code = item.get(ITEM_NAME)

    warehouse = item.get(WAREHOUSE_NAME)

    company_abbr = company_obj.abbr

    name = "{}:{}:{}".format(item_code, warehouse, company_abbr)

    warehouse_name = __get_format_warehouse_name(warehouse, company_abbr)

    script.append(name)
    script.append(item_code)
    script.append(WAREHOUSE_DEFAULT_DOCTYPE)
    script.append(ITEM_DOCTYPE)
    script.append(company_obj.name)
    script.append(warehouse_name)
    script.append(price_list.name)

    script += get_list_common()

    return tuple(script)

def __get_format_warehouse_name(warehouse, company_abbr):

    return "{0} - {1}".format(warehouse, company_abbr)


def __get_price_dict(price_item):

    return float(price_item) or 1
