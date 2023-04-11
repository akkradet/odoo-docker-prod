=========================
Web Dialog Confirm on Save
=========================

Show dialog to confirm or alert on form view after save a record:

- Add confirm="message" to show confirm, user can decide continue or cancel

- Add alert="message" to show alert after record has been saved

Example: <form string="Product" confirm="Are you sure to save this product?">


If you want to check condition to show dialog, add this function to model:

	@api.model

	def check_condition_show_dialog(self, record_id):
	   	return True

Return False to ignore show dialog after custom check
