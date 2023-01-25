import frappe
import requests
import json
from var_dump import var_dump
from base64 import b64encode
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import POST, GET
from gp_phonix_integration.gp_phonix_integration.exception import connection_exception

def send(callback, user, password, url, json_data = None):

    

    headers = __get_header(user, password)

    try:
   
        response = callback(headers)
        
        status_validate(response.status_code)

        response_json = response.json()

        return response_json

    except requests.exceptions.ConnectionError as error:

        raise connection_exception.ConnectionError()

    except connection_exception.Error401 as error:

        frappe.throw(str(error))

    except connection_exception.Error405 as error:

        frappe.throw(str(error))

    except connection_exception.ConnectionError as error:

        frappe.throw(str(error))

    except connection_exception.CompanyGPIntegrationError as error:

        frappe.throw(error.args)

    except Exception as error:
        
        frappe.throw(error.args)

        

def status_validate(status_code):

    if status_code == 401:

        raise connection_exception.Error401()

    if status_code == 405:

        raise connection_exception.Error405()

def send_petition(user, password, url, method, json_data = None):

    handle = None

    if method == GET:

        def handle(headers):

            return requests.get(url =url, params=json_data, headers = headers)

    if method == POST:

        def handle(headers):

            return requests.request("POST", url =url, data=json_data, headers = headers)


    return send(handle, user, password, url, json_data)

def get_api(endpoint_code):

    return frappe.get_doc("qp_GP_EndPoint", endpoint_code)

def get_enviroment(company_name):

    company = frappe.get_doc("Company", company_name)

    assert_company_has_gp_phonix_integration_setup(company.gp_phonix_integration_enviroment)

    return frappe.get_doc("qp_GP_Enviroment", company.gp_phonix_integration_enviroment)

def get_full_url(api_url, base_url):

    return "{}{}".format(base_url,api_url)

def execute_send(company_name, endpoint_code, json_data = None):

    api = get_api(endpoint_code)

    enviroment = get_enviroment(company_name)

    url = get_full_url(api.url, enviroment.base_url)

    return send_petition(enviroment.user, enviroment.password, url, api.request, json_data = json_data)


def __get_token(user, password):
    
	#endpoint = get_api(CONFIG)

    url = "http://104.210.4.91:8091/api/authenticate"

    payload =  json.dumps({
        "Username": user,
        "Password": password
    })

    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)

    reponse_token = json.loads(response.text)

    return reponse_token["Token"]

def __get_header(user, password):

    token = __get_token(user, password);

    return {
        "Authorization": "Bearer {}".format(token),
        "Content-Type": "application/json",
    }

def assert_company_has_gp_phonix_integration_setup(gp_phonix_integration_enviroment):

    if not gp_phonix_integration_enviroment:

        raise connection_exception.CompanyGPIntegrationError()