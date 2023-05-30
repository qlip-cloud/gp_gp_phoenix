import frappe

DOCTYPE = "qp_GP_ClassSync"
TABLE = "tabqp_GP_ClassSync"
VALUES = ("id", "code", "title", "class", "idlevel")
@frappe.whitelist()
def sync_class():

    
    sql = """insert INTO {} (name, id, code, title, class, idlevel)
        SELECT
            UUID()  as name,
            levelGroup.name as id,
            levelGroup.name as code,
            levelGroup.title as title,
            REPLACE(group_concat(distinct sku),","," ")  as class,
            level.idlevel as idlevel

        FROM tabqp_GP_Level as level
            
            inner join 
                tabqp_GP_LevelGroup as levelGroup
            on (levelGroup.name = level.group_type)

            inner join 
                tabItem as item
            on (levelGroup.name = item.qp_phonix_class)

        where levelGroup.name not in (select id from tabqp_GP_ClassSync)
        group by levelGroup.name, levelGroup.title
        """.format(TABLE)
    
    result_Categoria = frappe.db.sql(sql)

    #frappe.db.commit()

    return {
        "is_sync": True,
    }
