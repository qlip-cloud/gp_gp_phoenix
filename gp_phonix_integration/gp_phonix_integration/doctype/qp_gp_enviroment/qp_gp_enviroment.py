# Copyright (c) 2021, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from gp_phonix_integration.gp_phonix_integration.service.connection import get_token, get_api
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import AUTHENTICATE

class qp_GP_Enviroment(Document):
	
	def validate(self):

		get_token(self.user, self.password, self.base_url)

	
		
