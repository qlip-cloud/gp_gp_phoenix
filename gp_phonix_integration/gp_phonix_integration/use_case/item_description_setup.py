import frappe
from gp_phonix_integration.gp_phonix_integration.use_case.item_setup import get_items, uom_save, uom_conversion_name, UOM_BASE, ITEM_MULCANT, ITEM_NAME
from frappe.utils import now

@frappe.whitelist()
def sync(master_name, store_main = None):


    if not exist_item_sync_description_log_pending():

        #items_response, price_list, is_price_list_new = [1,2,3], 123, True
        items_response, price_list, is_price_list_new = get_items(master_name)   

        if items_response:

            item_sync_description_log = create_item_description_sync_log()

            frappe.enqueue(
                update_item,
                queue='long',                
                is_async=True,
                job_name="Item Description Sync Log",
                timeout=5400000,
                items_response = items_response,
                item_sync_description_log = item_sync_description_log
                
                )
            
        return {
            "item_sync_description_log_name": item_sync_description_log.name,
            "has_pending": False
        }

    return {
            "item_sync_description_log_name": None,
            "has_pending": True
        }

def update_item_sync_log(item_sync_description_log, is_sync =True):

    item_sync_description_log.is_sync = is_sync
    item_sync_description_log.is_complete = True
    item_sync_description_log.sync_finish = now()

    item_sync_description_log.save()

def create_item_description_sync_log():

    item_sync_log = frappe.new_doc("qp_GP_ItemDescriptionSyncLog")

    item_sync_log.insert()

    return item_sync_log

def exist_item_sync_description_log_pending():

    return frappe.db.exists("qp_GP_ItemDescriptionSyncLog", {
        "is_complete" : False
    })


def update_item(items_response, item_sync_description_log):
    
    uom_save(items_response)
    
    for item in items_response:
   
        update_description(item)
        
        update_uom(item)
        
    update_item_sync_log(item_sync_description_log)

    frappe.db.commit()
    
def update_description(item):

    
    
    sql = """
            UPDATE 
                tabItem
            SET
                qp_description_full = '{}', qp_phoenix_shortdescription = '{}'
            WHERE
                name = '{}'
            """.format(item["FullDescription"], item["ShortDescription"], item["IdItem"])
        
    frappe.db.sql(sql)
    
    
def update_uom(item):
    
    item_code = item.get(ITEM_NAME)
    
    name = uom_conversion_name(item_code, UOM_BASE)
    
    sql = """
        UPDATE 
            `tabUOM Conversion Detail`
        SET
            conversion_factor = {}
        WHERE
            name = '{}'
        """.format(item[ITEM_MULCANT], name)
        
    frappe.db.sql(sql)