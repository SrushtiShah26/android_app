import frappe
import requests
 
# /api/method/android.apisms.fetch_details
@frappe.whitelist()
def otp_fetch_details(otp,usr):
    authorization = frappe.db.get_single_value("Fast2SMS", "authorization")
    url = frappe.db.get_single_value("Fast2SMS", "url")
    route = frappe.db.get_single_value("Fast2SMS", "route")
    sender_id = frappe.db.get_single_value("Fast2SMS", "sender_id")
    language = frappe.db.get_single_value("Fast2SMS", "language")
    flash = frappe.db.get_single_value("Fast2SMS", "flash")

    message = 150624
    mobile=usr
    variables_values = f"{otp}"

    querystring = {"authorization":authorization,"sender_id":sender_id,"message":message,"variables_values":variables_values,"route":route,"numbers":mobile}

    headers = {
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    # print(response.text)
    return response.status_code