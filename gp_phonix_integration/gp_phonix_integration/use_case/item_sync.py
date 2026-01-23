from certifi import contents
import frappe
from erpnext.setup.utils import insert_record
import json
from gp_phonix_integration.gp_phonix_integration.service.item_sync import get_items, create_item_sync_log, update_item_sync_log, get_count_row, execute_sync_items, exist_item_sync_log_pending

UOM_BASE = "INQT"

from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup

@frappe.whitelist()
def handler(master_name, store_main = None):

    if not exist_item_sync_log_pending():
    #if True:
        master_setup = get_master_setup(master_name)

        items_response = get_items(master_setup)   
        #items_response, price_list, is_price_list_new = [1,2,3], 123, True

        if items_response:

            item_sync_log = create_item_sync_log()
            async_item(items_response = items_response, item_sync_log = item_sync_log)
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


def async_item(items_response, item_sync_log):
    
    count_items = execute_sync_items(items_response)
    
    count_insert_UOM = insert_UOM()
    
    count_insert_item_group = insert_item_group()
    
    count_update_items = update_items()

    count_insert_items = insert_items()
    
    count_insert_uom_convertion = insert_uom_convertion()
    
    update_item_sync_log(item_sync_log, count_items, count_insert_UOM, count_insert_item_group, count_update_items, count_insert_items, count_insert_uom_convertion)
    
    frappe.db.commit()
    
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

def insert_item_group():
    
    sql = """
        INSERT INTO `tabItem Group` (
            name, 
            item_group_name,
            is_group,
            modified,
            creation,
            modified_by,
            owner
        )
        SELECT 
            line.warehouse, 
            line.warehouse, 
            0, 
            NOW(),
            NOW(),
            'Administrator',
            'Administrator'
            
        FROM tabqp_GP_ItemSyncLines AS line
        LEFT JOIN `tabItem Group` AS item_group ON line.warehouse = item_group.name
        WHERE 
            item_group.name IS NULL 
            AND line.warehouse IS NOT NULL 
            AND line.warehouse <> ''
        GROUP BY line.warehouse"""
    
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

def insert_uom_convertion():
    
    sql = """
        INSERT INTO `tabUOM Conversion Detail` (
            name,
            parent,
            parentfield,
            parenttype,
            uom,
            conversion_factor,
            modified,
            creation,
            modified_by,
            owner
        )
        SELECT 
            CONCAT(line.name, ':', t_uom.uom_val) AS row_name,
            line.name,
            'uoms',
            'Item',
            t_uom.uom_val,
            CASE 
                WHEN t_uom.uom_val = 'UND' THEN 1.0
                ELSE COALESCE(
                    NULLIF(
                        NULLIF(TRIM(line.mulcant), ''), 
                    '0.000000'), 
                1.0)
            END,
            line.modified,
            NOW(),
            'Administrator',
            'Administrator'
        FROM `tabqp_GP_ItemSyncLines` AS line
        CROSS JOIN (
            SELECT 'UND' AS uom_val UNION ALL SELECT 'INQT'
        ) AS t_uom
        -- Buscamos si ya existe esta combinación específica de Item:UOM
        LEFT JOIN `tabUOM Conversion Detail` AS child 
            ON child.name = CONCAT(line.name, ':', t_uom.uom_val)
        WHERE 
            child.name IS NULL -- Solo si no existe la conversión
        """
    frappe.db.sql(sql)
    
    return get_count_row()