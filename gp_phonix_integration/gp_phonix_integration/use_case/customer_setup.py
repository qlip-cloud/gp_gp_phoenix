import frappe
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.service.command_sql import preparate_link_script, insert, select_sql, tuple_format, get_list_common, add_and_format_field, search_new as search_new_base
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import SYNCUSTOMER

CUSTOMER_NAME = "CustomerNumber"
CUSTOMER_GROUP_NAME = "CustomerClass"

CUSTOMER_TABLE = "tabCustomer"
CUSTOMER_GROUP_TABLE = "`tabCustomer Group`"
ADDRESS_TABLE = "tabAddress"
CONTACT_TABLE = "tabContact"
LINK_TABLE = "`tabDynamic Link`"
CONTACT_EMAIL_TABLE = "`tabContact Email`"

CONTACT_DOCTYPE = "Contact"
ADDRESS_DOCTYPE = "Address"
CUSTOMER_DOCTYPE = "Customer"

CUSTOMER_FIELDS = ["customer_name","name","disabled", "customer_group", "territory", "qp_typeid","qp_phonix_is_internal", "qp_phonix_has_sync", "qp_box_no_sku", "qp_box_sku", "incomplete_boxes", "qp_phoenix_buy_no_sku", "qp_vendor_required", "qp_credit_limit", "qp_credit_days", "qp_payment_term", "default_currency", "default_price_list", "is_frozen", "qp_phoenix_has_debt"]

ADDRESS_FIELDS = ["address_line1","address_line2","fax","phone","pincode","address_type","address_title","name","city","country","state", "email_id", "qp_address_id"]
LINK_FIELDS = ["name", "link_doctype", "link_name", "link_title", "parent", "parentfield", "parenttype"]
CONTACT_FIELDS = ["name", "first_name", "email_id", "qp_is_recipient"]
CONTACT_EMAIL_FIELDS = ["name", "parent", "parentfield", "parenttype", "email_id", "is_primary"]
CUSTOMER_GROUP_FIELDS = ["name","customer_group_name","parent_customer_group","old_parent", "gp_phonix_is_sync"]

@frappe.whitelist()
def sync_customer(master_name):

    master_setup = get_master_setup(master_name)

    default_country = get_company_country(master_setup.company)

    customer_list = get_customer_list(master_setup.company)
    #customer_list = mockList()
    
    
    if customer_list:

        root_customer_group = frappe.get_doc("Customer Group", {"is_group":1})

        customer_group_add = customer_group_save(customer_list, root_customer_group)

        count_customer_new, customer_add, customer_invalid, customer_repeat = customer_save(customer_list, root_customer_group, default_country)

        frappe.db.commit()

        return {
            "is_sync": True,
            "customer_total": len(customer_list),
            "customer_new": count_customer_new,
            "customer_add": customer_add,
            "customer_repeat": customer_repeat,
            "customer_invalid": customer_invalid,
            "customer_group_add": customer_group_add
        }
    return {
            "is_sync": False
        }
    
def customer_save(customer_list, root_customer_group, default_country):

    customer_new, count_repetat, count_whitespace, list_repeat = search_new(customer_list, CUSTOMER_NAME, CUSTOMER_TABLE)
    
    add_customer = 0
    count_invalid = 0
    count_whitespace = 0
    count_repetat = 0
    
    if customer_new:
        
        customer_config = get_customer_config(list_repeat)
        
        delete_customer(list_repeat)

        all_filter = filter_customer(customer_new, customer_list, root_customer_group, default_country, customer_config)

        add_customer = all_filter.get("add_customer")
        add_address = len(all_filter.get("list_address_script"))
        add_contact = len(all_filter.get("list_contact_script"))
        add_contact_email = len(all_filter.get("list_customer_script"))
        count_invalid = all_filter.get("count_invalid")

        if add_customer:

            insert(all_filter.get("list_customer_script"), CUSTOMER_FIELDS, CUSTOMER_TABLE)

            if add_address:
                #print(all_filter.get("list_address_script"))
                insert(all_filter.get("list_address_script"), ADDRESS_FIELDS, ADDRESS_TABLE)
                insert(all_filter.get("list_address_customer_script"), LINK_FIELDS, LINK_TABLE)

            if add_contact:
                                
                delete_contact(all_filter.get("contacts_name"))
                
                insert(all_filter.get("list_contact_script"), CONTACT_FIELDS, CONTACT_TABLE)
                
                insert(all_filter.get("list_contact_customer_script"), LINK_FIELDS, LINK_TABLE)

                if add_contact_email:
                    
                    insert(all_filter.get("list_contact_email_script"), CONTACT_EMAIL_FIELDS, CONTACT_EMAIL_TABLE)

    return len(customer_new), add_customer, count_invalid + count_whitespace, count_repetat

def filter_customer(customer_new, customer_list, root_customer_group, default_country, customer_config):

    territory = frappe.get_doc("Territory", {"is_group":1})

    customer_new_list = [customer for customer in customer_list if customer.get(CUSTOMER_NAME) in customer_new]

    contact_names = frappe.get_list("Contact", pluck="name")
    
    contact_config = get_contact_config(tuple(contact_names))
        
    list_customer_script = []
    list_address_script = []
    list_address_customer_script = []
    list_contact_script = []
    list_contact_customer_script = []
    list_contact_email_script = []
    whitelist = []
    count_invalid = 0
    contacts_name = []

    for customer in customer_new_list:

        if customer.get("CustomerName") != "":
        
            if validate_in_white_list(whitelist, customer.get("CustomerNumber")):
        
                is_email_valid = True if frappe.utils.validate_email_address(customer.get("Email")) else False

                customer_name = customer.get(CUSTOMER_GROUP_NAME) or root_customer_group.name

                customer_script = preparete_customer_script(customer, customer_name, territory.name, customer_config)

                list_customer_script.append(customer_script)

                if "ShipToAddress" in  customer and  customer.get("ShipToAddress") and customer.get("ShipToAddress") != "":

                    for key, address in enumerate(customer.get("ShipToAddress")):
                        
                        address_script , address_name= preparete_address_script(address, customer, default_country, is_email_valid, key)

                        address_customer_script = preparate_link_script(customer.get(CUSTOMER_NAME), address_name, ADDRESS_DOCTYPE, CUSTOMER_DOCTYPE)

                        list_address_script.append(address_script)

                        list_address_customer_script.append(address_customer_script)

                
                if customer.get("ContactPerson") != "":

                    contact_script, contact_name = preparate_contact_script(customer, is_email_valid, contact_config)
                    
                    contacts_name.append(contact_name)
                    
                    contact_customer_customer = preparate_link_script(customer.get(CUSTOMER_NAME), contact_name, CONTACT_DOCTYPE, CUSTOMER_DOCTYPE)

                    list_contact_script.append(contact_script)

                    list_contact_customer_script.append(contact_customer_customer)

                    if is_email_valid:

                        script_contact_email = preparate_contact_email_script(customer.get("Email"), contact_name)

                        list_contact_email_script.append(script_contact_email)
        else:

            count_invalid += 1
            


    return {
        "list_customer_script": tuple_format(list_customer_script), 
        "list_address_script" : tuple_format(list_address_script), 
        "list_address_customer_script" : tuple_format(list_address_customer_script), 
        "list_contact_script" : tuple_format(list_contact_script), 
        "list_contact_customer_script" : tuple_format(list_contact_customer_script),
        "list_contact_email_script" : tuple_format(list_contact_email_script),
        "add_customer": len(whitelist),
        "count_invalid": count_invalid,
        "contacts_name": tuple(contacts_name)
        
    }

def preparate_contact_email_script(email, contact_name):

    parentfield = "email_ids"
    is_primary = 1
    list_script = []
    
    name = "{}-{}".format(email, contact_name)
    
    list_script.append(name)
    list_script.append(contact_name)
    list_script.append(parentfield)
    list_script.append(CONTACT_DOCTYPE)
    list_script.append(email)
    list_script.append(is_primary)
    list_script += get_list_common()

    return tuple(list_script)

def preparate_contact_script(new_customer, is_email_valid, contact_config):

    list_script = []

    contact_name = "{}:{}- Contact Gp Phonix Integration".format(new_customer.get("CustomerNumber"), new_customer.get("ContactPerson"))

    list_script.append(contact_name)

    list_script.append(new_customer.get("ContactPerson"))

    email = new_customer.get("Email") if is_email_valid else ""
    
    list_script.append(email)
    
    list_script.append(contact_config[new_customer.get("CustomerNumber")].get("qp_is_recipient") if new_customer.get("CustomerNumber") in contact_config  else 0)
    list_script += get_list_common()

    return tuple(list_script), contact_name
    
def preparete_address_script(address, customer, default_country, is_email_valid, key):
    
    list_script = []
    #ADDRESS_FIELDS = ["address_line1","address_line2","fax","phone","pincode","address_type","address_title","name","city","country","state", "email_id"]
    adress_name = "{}:{}- Address Gp Phonix Integration{}".format(customer.get("CustomerNumber"), address.get("ShipToName"), f":{key}" if key > 0 else "")
    list_script.append(address.get("Address").strip())
    list_script.append(address.get("ShipToName") if "ShipToName" in address and address.get("ShipToName") else "")
    list_script.append(address.get("Phone2") if "Phone2" in address and address.get("Phone2") else "")
    list_script.append(address.get("Phone1") if "Phone1" in address and address.get("Phone1") else "")
    list_script.append(address.get("Zip") if "Zip" in address and address.get("Zip") else "")
    list_script.append("Shipping")
    list_script.append(adress_name)
    list_script.append(adress_name)
    list_script.append(address.get("City") if "City" in address and address.get("City") else "")
    list_script.append(customer.get("Country") if "Country" in customer and customer.get("Country") else default_country)
    list_script.append(address.get("State") if "State" in address and address.get("State") else "")
    
        
    email = customer.get("Email") if is_email_valid else ""

    list_script.append(email)
    list_script.append(address.get("AddressId") if "AddressId" in address and address.get("AddressId") else "")

    list_script += get_list_common()

    return tuple(list_script), adress_name

def preparete_customer_script(new_customer, customer_group_name, territory, customer_config):
       
    list_script = []

    customer_name = new_customer.get("CustomerName").replace(">","").replace("<","")
    
    list_script.append(customer_name)
    list_script.append(new_customer.get("CustomerNumber"))
    list_script.append(is_customer_disabled(new_customer))
    list_script.append(customer_group_name)
    list_script.append(territory)
    list_script.append("CC")
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_phonix_is_internal") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_phonix_has_sync") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_box_no_sku") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_box_sku") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("incomplete_boxes") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_phoenix_buy_no_sku") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_vendor_required") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(new_customer.get("CreditLimitAmount"))
    list_script.append(new_customer.get("CreditDays"))
    list_script.append(new_customer.get("PaymentTermsId"))
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("default_currency") if new_customer.get("CustomerNumber") in customer_config else None)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("default_price_list") if new_customer.get("CustomerNumber") in customer_config else None)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("is_frozen") if new_customer.get("CustomerNumber") in customer_config else 0)
    list_script.append(customer_config[new_customer.get("CustomerNumber")].get("qp_phoenix_has_debt") if new_customer.get("CustomerNumber") in customer_config else 0)

    list_script += get_list_common()

    return tuple(list_script)

def customer_group_save(customer_list, root_customer_group):

    customer_group_new, count_repetat, count_whitespace = search_new_base(customer_list, CUSTOMER_GROUP_NAME, CUSTOMER_GROUP_TABLE)

    if customer_group_new:

        custom_script = preparate_customer_group_script(customer_group_new, root_customer_group)
        
        insert(custom_script, CUSTOMER_GROUP_FIELDS, CUSTOMER_GROUP_TABLE)

    return len(customer_group_new)

def preparate_customer_group_script(customer_group_new_list, root_customer_group):
    
    list_script = []

    for new_customer_group in customer_group_new_list:

        script = []
        script.append(new_customer_group)
        script.append(new_customer_group)
        script.append(root_customer_group.name)
        script.append(root_customer_group.name)
        script.append(True)
        script += get_list_common()

        list_script.append(tuple(script))

    return tuple_format(list_script)    

def get_customer_list(company_name):

    customer_respose = execute_send(company_name = company_name, endpoint_code = SYNCUSTOMER)

    return customer_respose.get("CustomersInfo")

def get_company_country(company_name):

    company = frappe.get_doc("Company", company_name)

    return company.country

def validate_in_white_list(whitelist, customer_number):

    if [True for x in whitelist if x == customer_number]:

        return False
    
    whitelist.append(customer_number)

    return True

def is_customer_disabled(customer):

    return True if customer.get("Hold") == "Yes" or customer.get("Inactive") == "Yes" else False
        
def delete_contact(contact_ids):
    
    sql = f"""DELETE FROM `tabContact Email` 
        WHERE `parent` IN {contact_ids};"""
        
    frappe.db.sql(sql)
    
    
    sql = f"""DELETE FROM `tabDynamic Link` 
    WHERE `parenttype` = 'Contact' AND `parent` in {contact_ids};"""

    frappe.db.sql(sql)
    
    sql = f"""DELETE FROM `tabContact` where name in {contact_ids};"""
    frappe.db.sql(sql)
    
          
def delete_customer(customer_ids):
    
    sql = f"""DELETE FROM `tabAddress` 
        WHERE `name` IN (
            SELECT `parent` FROM `tabDynamic Link` 
            WHERE `link_doctype` = 'Customer' AND `link_name` in {customer_ids} AND `parenttype` = 'Address'
        );"""
        
        
    frappe.db.sql(sql)
    
    sql = f"""DELETE FROM `tabDynamic Link` 
    WHERE `link_doctype` = 'Customer' AND `link_name` in {customer_ids} AND `parenttype` = 'Address';"""
    
    frappe.db.sql(sql)

    sql = f"""DELETE FROM `tabCustomer` 
    WHERE `name` in {customer_ids};"""
    
    frappe.db.sql(sql)
    
def search_new_and_duplicate(list_base, id_base, table, add_default = [], is_id_upper = False):

    list_total = list(map(lambda x: x.get(id_base).upper() if is_id_upper else  x.get(id_base), list_base))
    
    list_total += add_default
    
    list_no_repeat = list(set(list_total))

    list_name = list(filter(lambda x: x != "", list_no_repeat))

    list_repeat =  select_sql(table, list_name, is_id_upper)
    
    count_repeat = len(list_total) - len(list_no_repeat)

    count_whitespace = len(list_no_repeat) -len(list_name)
    
    return list_name, count_repeat, list_repeat, count_whitespace

def search_new(list_base, id_base, table, add_default = [], is_id_upper = False):

    list_new, count_repeat, list_repeat, count_whitespace =search_new_and_duplicate(list_base, id_base, table, add_default, is_id_upper)

    return list_new, count_repeat, count_whitespace, tuple(list_repeat)

def get_customer_config(list_repeat):
    
    search = "*"
    
    where = f"name IN {list_repeat}"
    
    results = select_custom_sql(search, CUSTOMER_TABLE, where)
    
    confis = {}
    
    for line in results:
        
        confis[line["name"]] = {
            "qp_phonix_is_internal" : line["qp_phonix_is_internal"],
            "qp_phonix_has_sync" : line["qp_phonix_has_sync"],
            "qp_box_no_sku" : line["qp_box_no_sku"],
            "qp_box_sku" : line["qp_box_sku"],
            "incomplete_boxes" : line["incomplete_boxes"],
            "qp_phoenix_buy_no_sku": line["qp_phoenix_buy_no_sku"],
            "qp_vendor_required": line["qp_vendor_required"],
            "default_currency": line["default_currency"] or "",
            "default_price_list": line["default_price_list"] or "",
            "is_frozen": line["is_frozen"] or 0,
            "qp_phoenix_has_debt": line["qp_phoenix_has_debt"] or 0
            
        }
        
    return confis

def get_contact_config(contacts_name):
    
    search = "name, qp_is_recipient"
    
    where = f"name IN {contacts_name}"
    
    results = select_custom_sql(search, CONTACT_TABLE, where)
    
    confis = {}
    
    for line in results:
        
        confis[line["name"]] = {
            "qp_is_recipient" : line["qp_is_recipient"]
        }
        
    return confis

def select_custom_sql(search, table, condition):

    search_customer_sql = """ 
        Select
            {}
        FROM
            {}
        WHERE
            {}
    """.format(search, table, condition)
    return frappe.db.sql(search_customer_sql, as_dict=1)