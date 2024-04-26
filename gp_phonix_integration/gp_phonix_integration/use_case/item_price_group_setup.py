import frappe
from gp_phonix_integration.gp_phonix_integration.use_case.item_setup import get_items
from frappe.utils import now

@frappe.whitelist()
def sync(master_name, store_main = None):


    if not exist_item_sync_price_group_log_pending():

        #items_response, price_list, is_price_list_new = [1,2,3], 123, True
        items_response, price_list, is_price_list_new = get_items(master_name)   
        
        if items_response:

            item_sync_price_group_log = create_item_price_group_sync_log()

            frappe.enqueue(
                update_item,
                queue='long',                
                is_async=True,
                #now=True,
                job_name="Item Price Group Sync Log",
                timeout=5400000,
                items_response = items_response,
                item_sync_price_group_log = item_sync_price_group_log
                
                )
            
        return {
            "item_sync_price_group_log_name": item_sync_price_group_log.name,
            "has_pending": False
        }

    return {
            "item_sync_price_group_log_name": None,
            "has_pending": True
        }

def update_item_sync_log(item_sync_price_group_log, is_sync =True):

    item_sync_price_group_log.is_sync = is_sync
    item_sync_price_group_log.is_complete = True
    item_sync_price_group_log.sync_finish = now()

    item_sync_price_group_log.save()

def create_item_price_group_sync_log():

    item_sync_log = frappe.new_doc("qp_GP_ItemPriceGroupSyncLog")

    item_sync_log.insert()

    return item_sync_log

def exist_item_sync_price_group_log_pending():

    return frappe.db.exists("qp_GP_ItemPriceGroupSyncLog", {
        "is_complete" : False
    })


def update_item(items_response, item_sync_price_group_log):

    update_json = preparate_update_item(items_response)
    
    exec_update_item(update_json)

    update_item_sync_log(item_sync_price_group_log)

    frappe.db.commit()


def preparate_update_item(items_response):

    update_json = {}

    for item in items_response:

        if item["PriceGroup"] not in update_json:

            update_json[item["PriceGroup"]] = []

        update_json[item["PriceGroup"]].append(item["IdItem"])

    return update_json


def exec_update_item(update_json):

    for key, value in update_json.items():

        value = str(value).replace("[", "(").replace("]", ")")

        sql = """
            UPDATE 
                tabItem
            SET
                qp_price_group = '{}' 
            WHERE
                name in {}
            """.format(key, value)
        
        frappe.db.sql(sql)