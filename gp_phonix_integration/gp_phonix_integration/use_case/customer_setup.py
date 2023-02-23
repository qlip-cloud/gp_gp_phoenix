import frappe
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.service.command_sql import preparate_link_script, insert, search_new, tuple_format, get_list_common, add_and_format_field
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

CUSTOMER_FIELDS = ["customer_name","name","disabled", "customer_group", "territory", "qp_typeid"]
ADDRESS_FIELDS = ["address_line1","address_line2","fax","phone","pincode","address_type","address_title","name","city","country","state", "email_id"]
LINK_FIELDS = ["name", "link_doctype", "link_name", "link_title", "parent", "parentfield", "parenttype"]
CONTACT_FIELDS = ["name", "first_name", "email_id"]
CONTACT_EMAIL_FIELDS = ["name", "parent", "parentfield", "parenttype", "email_id", "is_primary"]
CUSTOMER_GROUP_FIELDS = ["name","customer_group_name","parent_customer_group","old_parent", "gp_phonix_is_sync"]

@frappe.whitelist()
def sync_customer(master_name):

    master_setup = get_master_setup(master_name)

    default_country = get_company_country(master_setup.company)

    customer_list = get_customer_list(master_setup.company)
    
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

    customer_new, count_repetat, count_whitespace= search_new(customer_list, CUSTOMER_NAME, CUSTOMER_TABLE)
    add_customer = 0
    count_invalid = 0
    count_whitespace = 0
    count_repetat = 0
    if customer_new:

        all_filter = filter_customer(customer_new, customer_list, root_customer_group, default_country)

        add_customer = all_filter.get("add_customer")
        add_address = len(all_filter.get("list_address_script"))
        add_contact = len(all_filter.get("list_contact_script"))
        add_contact_email = len(all_filter.get("list_customer_script"))
        count_invalid = all_filter.get("count_invalid")

        if add_customer:

            insert(all_filter.get("list_customer_script"), CUSTOMER_FIELDS, CUSTOMER_TABLE)

            if add_address:
                
                insert(all_filter.get("list_address_script"), ADDRESS_FIELDS, ADDRESS_TABLE)
                insert(all_filter.get("list_address_customer_script"), LINK_FIELDS, LINK_TABLE)

            if add_contact:
                
                insert(all_filter.get("list_contact_script"), CONTACT_FIELDS, CONTACT_TABLE)
                insert(all_filter.get("list_contact_customer_script"), LINK_FIELDS, LINK_TABLE)

                if add_contact_email:
                    
                    insert(all_filter.get("list_contact_email_script"), CONTACT_EMAIL_FIELDS, CONTACT_EMAIL_TABLE)

    return len(customer_new), add_customer, count_invalid + count_whitespace, count_repetat

def filter_customer(customer_new, customer_list, root_customer_group, default_country):

    territory = frappe.get_doc("Territory", {"is_group":1})

    customer_new_list = [customer for customer in customer_list if customer.get(CUSTOMER_NAME) in customer_new]

    list_customer_script = []
    list_address_script = []
    list_address_customer_script = []
    list_contact_script = []
    list_contact_customer_script = []
    list_contact_email_script = []
    whitelist = []
    count_invalid = 0

    for customer in customer_new_list:

        if customer.get("CustomerName") != "":
        
            if validate_in_white_list(whitelist, customer.get("CustomerNumber")):
        
        
                is_email_valid = True if frappe.utils.validate_email_address(customer.get("Email")) else False

                customer_name = customer.get(CUSTOMER_GROUP_NAME) or root_customer_group.name

                customer_script = preparete_customer_script(customer, customer_name, territory.name)

                list_customer_script.append(customer_script)

                if customer.get("Address1") != "":

                    address_script , address_name= preparete_address_script(customer, default_country, is_email_valid)

                    address_customer_script = preparate_link_script(customer.get(CUSTOMER_NAME), address_name, ADDRESS_DOCTYPE, CUSTOMER_DOCTYPE)

                    list_address_script.append(address_script)

                    list_address_customer_script.append(address_customer_script)

                if customer.get("ContactPerson") != "":

                    contact_script, contact_name = preparate_contact_script(customer, is_email_valid)
                    
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
        "count_invalid": count_invalid
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

def preparate_contact_script(new_customer, is_email_valid):

    list_script = []

    contact_name = "{}:{}- Contact Gp Phonix Integration".format(new_customer.get("CustomerNumber"), new_customer.get("ContactPerson"))

    list_script.append(contact_name)

    list_script.append(new_customer.get("ContactPerson"))

    email = new_customer.get("Email") if is_email_valid else ""
        
    list_script.append(email)

    list_script += get_list_common()

    return tuple(list_script), contact_name
    
def preparete_address_script(new_customer, default_country, is_email_valid):
    
    list_script = []
    
    adress_name = "{}:{}- Address Gp Phonix Integration".format(new_customer.get("CustomerNumber"), new_customer.get("CustomerName"))
    list_script.append(new_customer.get("Address1"))
    list_script.append(new_customer.get("Address2"))
    list_script.append(new_customer.get("Fax"))
    list_script.append(new_customer.get("Phone1"))
    list_script.append(new_customer.get("Zip"))
    list_script.append("Shipping")
    list_script.append(adress_name)
    list_script.append(adress_name)
    list_script.append(new_customer.get("City"))
    list_script.append(new_customer.get("Country") if new_customer.get("Country") else default_country)
    list_script.append(new_customer.get("State"))

    email = new_customer.get("Email") if is_email_valid else ""

    list_script.append(email)

    list_script += get_list_common()

    return tuple(list_script), adress_name

def preparete_customer_script(new_customer, customer_group_name, territory):
       
    list_script = []
    
    customer_name = new_customer.get("CustomerName").replace(">","").replace("<","")
    
    list_script.append(customer_name)
    list_script.append(new_customer.get("CustomerNumber"))
    list_script.append(is_customer_disabled(new_customer))
    list_script.append(customer_group_name)
    list_script.append(territory)
    list_script.append("CC")
    
    list_script += get_list_common()

    return tuple(list_script)

def customer_group_save(customer_list, root_customer_group):

    customer_group_new, count_repetat, count_whitespace = search_new(customer_list, CUSTOMER_GROUP_NAME, CUSTOMER_GROUP_TABLE)

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