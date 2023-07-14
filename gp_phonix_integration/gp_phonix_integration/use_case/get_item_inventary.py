import frappe
import json
import random
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import CHECKOUTART,LEVELS

def handler(item_list):

    name = "name"
    
    return __search_inventary(item_list, name)

def get_item_order(item_list):

    name = "item_code"

    return __search_inventary(item_list, name) 

def __search_inventary(item_list = [], name = None):
    
    item_name = list(map(lambda item: {"Id": item[name]},item_list))

    store_main = __get_basic_params()

    companies = frappe.db.get_all("Company", pluck='name')

    json_data = json.dumps({
        "Items": item_name,
        "Warehouses": __get_basic_params() 
    })

    print("inicio")
    response =  execute_send(company_name = companies[0], endpoint_code = CHECKOUTART, json_data = json_data)
    print(response)
    print("fin")

    for item in item_list:

        inventaies = list(filter(lambda inventary: item[name] == inventary["IdItem"], response["Items"]))
        
        item.setdefault("quantity", sum(float(inventary["Quantity"]) for inventary in inventaies))

        item.setdefault("quantity_dis", sum(float(inventary.get("QuantityDis", 0)) for inventary in inventaies))

        #item.setdefault("quantity", random.choice([5800, 100124, 50124, 5491, 85416845]))
        #item.setdefault("quantity_dis", random.choice([0, 100, 50, 0, 0]))
    

    return item_list

def __get_basic_params():

    store_mains = frappe.db.get_all("qp_GP_MasterSetup",{
        "is_active": True
    },["store_main"]);
    
    
    warehouses = [
        {"Id": get_id(store_main["store_main"])} for store_main in store_mains
    ]

    return warehouses

def get_id(string_complete):

    list_string = string_complete.split("|")

    return list_string[0]
