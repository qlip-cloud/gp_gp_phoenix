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

from gp_phonix_integration.gp_phonix_integration.service.item_sync import get_items_and_price_list, create_item_sync_log, execute_sync_items, update_item_sync_log, get_count_row, exist_item_sync_log_pending

@frappe.whitelist()

def handler(master_name, store_main = None):

    if not exist_item_sync_log_pending():
    #if True:
        
        master_setup = get_master_setup(master_name)

        items_response, price_level = get_items_and_price_list(master_setup)   

        if items_response:

            item_sync_log = create_item_sync_log()
            
            async_item(items_response = items_response, price_level = price_level, item_sync_log = item_sync_log)
            
        return {
            "item_sync_log_name": item_sync_log.name,
            "has_pending": False
        }

    return {
            "item_sync_log_name": None,
            "has_pending": True
        }

def async_item(items_response, price_level, item_sync_log):
        
    count_items = execute_sync_items(items_response)
    
    count_price_item_add = 0
    
    count_price_item_update = 0
    
    count_price_list_add = price_list_add(price_level)
    
    count_price_item_add = price_item_add(price_level)
        
    count_price_item_update = price_item_update(price_level)
  
    update_item_sync_log(item_sync_log, count_price_list_add = count_price_list_add, count_price_item_add = count_price_item_add, count_price_item_update = count_price_item_update)
    
    frappe.db.commit()
        
def price_list_add(price_level):
    
    sql = f"""
    INSERT INTO `tabPrice List` (
        name, 
        price_list_name, 
        currency, 
        selling, 
        enabled, 
        buying,
        price_not_uom_dependent,
        qp_without_discount,
        modified, 
        creation, 
        modified_by, 
        owner, 
        docstatus
    )
    SELECT 
        src.p_name,
        src.p_name,
        src.p_curr,
        1, 1, 0, 0, 0,
        NOW(), NOW(),
        'Administrator', 'Administrator', 0
    FROM (
        SELECT '{price_level}' AS p_name, 'COP' AS p_curr
        UNION SELECT '{price_level} USD', 'USD'
        UNION SELECT '{price_level} EUR', 'EUR'
    ) AS src
    -- Validamos contra la tabla real para ver si ya existe el nombre
    LEFT JOIN `tabPrice List` AS target ON src.p_name = target.name
    WHERE target.name IS NULL;
    """
    
    frappe.db.sql(sql)
    
    return get_count_row()

def price_item_add(price_level):
    
    sql = f"""
    INSERT INTO `tabItem Price` (
        name,
        item_code,
        item_name,
        item_description,
        price_list,
        price_list_rate,
        valid_from,
        creation,
        modified,
        modified_by,
        owner,
        docstatus
    )
    SELECT 
        CONCAT(line.id_item, ':', t_list.list_name) AS generated_name,
        line.id_item,
        line.description,
        line.description,
        t_list.list_name,
        CASE 
            WHEN t_list.list_name = '{price_level}'     THEN COALESCE(NULLIF(REPLACE(line.price, ',', '.'), ''), 0)
            WHEN t_list.list_name = '{price_level} EUR' THEN COALESCE(NULLIF(REPLACE(line.price_eu, ',', '.'), ''), 0)
            WHEN t_list.list_name = '{price_level} USD' THEN COALESCE(NULLIF(REPLACE(line.price_usd, ',', '.'), ''), 0)
        END AS rate,
        CURDATE(),
        NOW(),
        NOW(),
        'Administrator',
        'Administrator',
        0
    FROM `tabqp_GP_ItemSyncLines` AS line
    CROSS JOIN (
        SELECT '{price_level}' AS list_name 
        UNION ALL SELECT '{price_level} EUR' 
        UNION ALL SELECT '{price_level} USD'
    ) AS t_list
    -- Un INNER JOIN asegura que el Item exista en el sistema
    INNER JOIN `tabItem` AS item ON line.id_item = item.item_code
    -- Validamos que NO exista ya ese nombre (Item:Lista)
    LEFT JOIN `tabItem Price` AS existing_price 
        ON existing_price.name = CONCAT(line.id_item, ':', t_list.list_name)
    WHERE 
        existing_price.name IS NULL
        """
    print(sql)
    frappe.db.sql(sql)
    
    return get_count_row()  

def price_item_update(price_level):
    
    sql = f"""
        UPDATE `tabItem Price` AS tP
        INNER JOIN (
            -- Primero preparamos los datos de origen "triplicados" para poder comparar
            SELECT 
                line.id_item,
                t_list.list_name,
                CASE 
                    WHEN t_list.list_name = '{price_level}'     THEN COALESCE(NULLIF(REPLACE(line.price, ',', '.'), ''), 0)
                    WHEN t_list.list_name = '{price_level} EUR' THEN COALESCE(NULLIF(REPLACE(line.price_eu, ',', '.'), ''), 0)
                    WHEN t_list.list_name = '{price_level} USD' THEN COALESCE(NULLIF(REPLACE(line.price_usd, ',', '.'), ''), 0)
                END AS source_rate,
                line.modified AS source_modified
            FROM `tabqp_GP_ItemSyncLines` AS line
            CROSS JOIN (
                SELECT '{price_level}' AS list_name 
                UNION ALL SELECT '{price_level} EUR' 
                UNION ALL SELECT '{price_level} USD'
            ) AS t_list
        ) AS src ON tP.name = CONCAT(src.id_item, ':', src.list_name)
        SET 
            tP.price_list_rate = src.source_rate,
            tP.modified = src.source_modified
        WHERE NOT (tP.price_list_rate <=> src.source_rate)
    """
    
    frappe.db.sql(sql)
    
    return get_count_row()