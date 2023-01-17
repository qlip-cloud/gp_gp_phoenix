# Copyright (c) 2021, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import json

class qp_GP_Store(Document):
	pass
	"""def load_from_db(self):
		print("########################1#############################")
		print(self.doctype, self.name)
		pass
		#super(Document, self).__init__(d)
	
	def get_list(self, args):
		
		print("########################2#############################")
		print(self.doctype, self.name)
		
		return json.loads('[{"store_name":"uno","name":"uno"},{"store_name":"dos","name":"dos"}]')

	def onload(self, args):

		print("########################3#############################")
		print(self.doctype, self.name)
		return json.loads('[{"store_name":"uno","name":"uno"},{"store_name":"dos","name":"dos"}]')"""