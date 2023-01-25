import frappe
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import LEVELS
from gp_phonix_integration.gp_phonix_integration.service.command_sql import update_sql, get_list_common, insert_sql

LEVEL_TABLE = "tabqp_GP_Level"
LEVEL_FIELDS = "(name, idlevel, level, currency, discountpercentage, group_type, creation, modified, modified_by, owner)"

@frappe.whitelist()
def sync_level(master_name):

    customer_group_list = frappe.db.get_list("Customer Group",{"gp_phonix_is_sync": True}, pluck = "name")

    master_setup = get_master_setup(master_name)

    total = 0

    count_created = 0

    count_updated = 0

    for customer_group in customer_group_list:
        
        payload = json.dumps({
            "IdLevel": customer_group
        })

        level_list = get_level_list(master_setup.company, payload)
        
        total += len(level_list)

        levels_new = list(filter(lambda level: not frappe.db.exists("qp_GP_Level", level["IdLevel"]+level["Group"]), level_list))
        
        count_created+=len(levels_new)

        list_insert = []

        for level_new in levels_new:
            
            list_insert.append(preparate_level_script(level_new))

        """    else:

                set_expression = 
                    DiscountPercentage = {DiscountPercentage}
                .format(DiscountPercentage = level["DiscountPercentage"])

                where_expresion = 
                    IdLevel = '{IdLevel}' and
                    Group = '{Group}'
                .format(level["IdLevel"], level["Group"])
                
                update_sql("tabqp_GP_Level", set_expression, where_expresion)"""

        if levels_new:

            values = str(list_insert).replace("[","").replace("]","")

            insert_sql(LEVEL_TABLE, LEVEL_FIELDS, values)
            
            frappe.db.commit()

    return get_sync_response(True, total, count_created, count_updated)

def get_sync_response(is_sync, total = 0, count_created = 0, count_updated = 0):
    
    response = {
            "is_sync": False
        }

    if is_sync:
        
        response.update({
            "is_sync": is_sync,
            "total": total,
            "count_created": count_created,
            "count_updated": count_updated
        })

    return response

def preparate_level_script(level):

    now = frappe.utils.now()

    username = "Administrator"

    name = level["IdLevel"]+level["Group"]

    list_script = tuple([name,level["IdLevel"], level["Level"], level["Currency"],float(level["DiscountPercentage"]), level["Group"], now,now,username,username])
        

    return list_script

def get_level_list(company, payload):

    level_respose = execute_send(company_name = company, endpoint_code = LEVELS, json_data = payload)

    return level_respose.get("Levels")