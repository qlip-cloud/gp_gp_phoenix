import frappe

def insert(script, fields_base, table):

    fields = add_and_format_field(fields_base)

    return insert_sql(table, fields, script)

def preparate_link_script(customer_name, origin_name, parenttype, link_doctype):
    
    list_script = []

    name = "{}-{}".format(customer_name, origin_name)

    list_script.append(name)
    list_script.append(link_doctype)
    list_script.append(customer_name)
    list_script.append(customer_name)
    list_script.append(origin_name)
    list_script.append("links")
    list_script.append(parenttype)

    list_script += get_list_common()
    
    return tuple(list_script)

def get_list_common():

    now = frappe.utils.now()

    user_name = "Administrator"
    
    list_common = []

    list_common.append(now)
    list_common.append(now)
    list_common.append(user_name)
    list_common.append(user_name)

    return list_common

def tuple_format(list_format):

    return str(list_format).replace("[","").replace("]","")

def search_new(list_base, id_base, table, add_default = [], is_id_upper = False):

    list_new, count_repeat, list_repeat, count_whitespace =search_new_and_duplicate(list_base, id_base, table, add_default, is_id_upper)

    return list_new, count_repeat, count_whitespace

def search_new_and_duplicate(list_base, id_base, table, add_default = [], is_id_upper = False):

    list_total = list(map(lambda x: x.get(id_base).upper() if is_id_upper else  x.get(id_base), list_base))
    
    list_total += add_default
    
    list_no_repeat = list(set(list_total))

    list_name = list(filter(lambda x: x != "", list_no_repeat))

    list_repeat =  select_sql(table, list_name, is_id_upper)

    list_new = [name for name in list_name if name not in list_repeat]

    count_repeat = len(list_total) - len(list_no_repeat)

    count_whitespace = len(list_no_repeat) -len(list_name)
    
    return list_new, count_repeat, list_repeat, count_whitespace

def add_and_format_field(fields_origin):

    fields_base = ["creation", "modified", "modified_by", "owner"]

    fields_tuple = tuple(fields_origin + fields_base)

    fields_str = str(fields_tuple)

    return fields_str.replace("'","")

def select_sql(table, list_search, is_id_upper = False):

    field_name = is_id_upper and "UPPER(name)" or "name"

    search_customer_sql = """ 
        Select
            {}
        FROM
            {}
        WHERE
            name IN {}
    """.format(field_name, table, list_converter(list_search))

    result_sql = list(frappe.db.sql(search_customer_sql))

    return list(map(lambda x: str(x[0]), result_sql))


def select_custom_sql(search, table, condition):

    search_customer_sql = """ 
        Select
            {}
        FROM
            {}
        WHERE
            {}
    """.format(search, table, condition)

    return list(frappe.db.sql(search_customer_sql))

def insert_sql(table, values, script):

    string = """
    INSERT
        
    INTO
        {} {}
    VALUES
        {}
    """.format(table, values, script)

    #save_log(string)
    
    print(string)
    result = frappe.db.sql(string)

    return string, result

"update <table> set <column>=<expression> where <condition1>"

def update_sql(table, set_expression, where_expresion):

    string = """
    UPDATE
        {}
    SET
        {}
    where
        {}
    """.format(table, set_expression, where_expresion)
  
    frappe.db.sql(string)

def list_converter(list_format):

    return str(list_format).replace("[","(").replace("]",")")

def save_log(text):

    with open('/workspace/development/frappe/apps/gp_phonix_integration/gp_phonix_integration/gp_phonix_integration/use_case/response.txt', 'a') as f:
                
        f.write(str(text))
        f.write("\n")