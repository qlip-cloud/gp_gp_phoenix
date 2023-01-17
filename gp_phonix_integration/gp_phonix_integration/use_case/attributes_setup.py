import frappe


@frappe.whitelist()
def sync_attributes():

    _update_attributes_code()

    frappe.db.commit()

    return {
        "is_sync": True,
    }


def _update_attributes_code():

    string = """
        UPDATE tabqp_ItemAttribute
        inner join tabItem on tabqp_ItemAttribute.parent = tabItem.name and tabqp_ItemAttribute.parentfield = 'item_attributes'
        SET tabqp_ItemAttribute.code_id = SUBSTRING(SHA1(LCASE(CONCAT(tabItem.item_group,tabqp_ItemAttribute.value))),16)
    """
    
    result = frappe.db.sql(string)

    # TODO: result_SubCategoria y result_Categoria. Acción temporal para actualizar BD existentes con valley Floral

    string = """
        UPDATE tabqp_ItemAttribute
        SET attribute = 'SubCategoria'
        WHERE attribute = 'color'
    """

    result_SubCategoria = frappe.db.sql(string)

    string = """
        UPDATE tabqp_ItemAttribute
        SET attribute = 'Categoria'
        WHERE attribute = 'type'
    """

    result_Categoria = frappe.db.sql(string)

    return True
