# Copyright (c) 2021, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from gp_phonix_integration.gp_phonix_integration.service.connection import send_petition, get_api
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import CONFIG

class qp_GP_Enviroment(Document):
	


	def validate(self):

		endpoint = get_api(CONFIG)

		url_validate = "{}{}".format(self.base_url, endpoint.url)

		send_petition(self.user, self.password, url_validate, endpoint.request)

	
		
