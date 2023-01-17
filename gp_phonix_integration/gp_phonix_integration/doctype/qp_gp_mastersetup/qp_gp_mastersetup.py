# Copyright (c) 2021, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class qp_GP_MasterSetup(Document):
	
	def get_store_id_main(self):
		return self.__get_id_string(self.store_main)

	def get_store_id_secundary(self):

		return list(map(lambda x: x.store, self.store_secundary))

	def __get_id_string(self, string_complete):

		list_string = string_complete.split("|")

		return list_string[0]



