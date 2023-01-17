import frappe
from frappe.utils import comma_and
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import SYNSHIPPING


@frappe.whitelist()
def sync_shipping_method(master_name):

    master_setup = get_master_setup(master_name)

    shipping_list = get_shipping_list(master_setup.company)

    sync_response = add_or_update_shipping(shipping_list)

    frappe.log_error(sync_response, title="Sync Result")

    return sync_response


def get_shipping_list(company):

    shipping_respose = execute_send(company_name = company, endpoint_code = SYNSHIPPING)

    return shipping_respose.get("Customers")


def add_or_update_shipping(shipping_list):

    dict_error = []

    count_update = 0

    customer_name = ""

    shipping_customer = []

    for shipping_iter in shipping_list:

        customer_iter = shipping_iter.get("CustomerNumber")

        sm_iter = shipping_iter.get("ShippingMethods")

        if frappe.db.exists("Customer", {"name": customer_iter}) and frappe.db.exists("qp_GP_ShippingType", {"name": sm_iter}):

            if customer_name != customer_iter and customer_name:

                __update_customer(customer_name, shipping_customer)

                count_update += 1

                customer_name = customer_iter

                shipping_customer = []
                
            else:

                customer_name = customer_iter
            
            shipping_customer.append(sm_iter)

        else:
 
            dict_error.append('{}:{}'.format(customer_iter, sm_iter))

    if customer_name:

        __update_customer(customer_name, shipping_customer)

        count_update += 1

    return {
        'total_items': len(shipping_list),
        'count_cust_upd': count_update,
        'mess_error': comma_and(dict_error, add_quotes=False)
    }

def __update_customer(customer_name, shipping_customer):

    customer = frappe.get_doc('Customer', customer_name)

    customer.gp_shipping_method = []

    for shipping_customer_item in shipping_customer:

        customer.append('gp_shipping_method', __create_shipping_method_object(shipping_customer_item))

    customer.save()


def __create_shipping_method_object(shipping_customer_item):

    return {
        'shipping_method': shipping_customer_item
    }