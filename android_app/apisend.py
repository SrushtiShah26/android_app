import frappe
import string
import requests

from mimetypes import guess_type
from frappe.utils.image import optimize_image
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from frappe.core.doctype.file.file import File
	from frappe.core.doctype.user.user import User
        
ALLOWED_MIMETYPES = (
	"image/png",
	"image/jpeg",
	"application/pdf",
	"application/msword",
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	"application/vnd.ms-excel",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	"application/vnd.oasis.opendocument.text",
	"application/vnd.oasis.opendocument.spreadsheet",
	"text/plain",
)
from frappe import _, is_whitelisted
from frappe.utils import cint

from random import choice
from datetime import datetime, timedelta
from android_app.apisms import otp_fetch_details
from frappe.auth import LoginManager
from frappe.handler import upload_file

# This is to create the android user with the help of button
# /api/method/android_app.apisend.android_user_creation
@frappe.whitelist()
def android_user_creation():
    email = frappe.form_dict["email"]
    new_password = frappe.form_dict["new_password"]
    cell_number = frappe.form_dict["cell_number"]
    doc = frappe.new_doc('User')
    doc.username = email
    doc.email = email
    doc.first_name = email
    doc.new_password = new_password
    doc.send_welcome_email = 0
    doc.mobile_no = cell_number
    doc.role_profile_name = "Driver"
    doc.insert()
    frappe.db.commit()

    subject = frappe.db.get_value('User', email, 'name')
    api_generate = generate_keys(subject)
    frappe.db.set_value('User', subject, 'user_type', 'System User')
    frappe.db.set_value('User', subject,'api_key', api_generate[1])
    frappe.db.commit()
    
    doc = frappe.new_doc('OTP')
    doc.user = subject
    doc.insert()
    frappe.db.commit() 

    otp_name=frappe.db.get_value('OTP', subject, 'name')
    otp_name_function=otp_checking(subject)

    frappe.response["msg"]=subject


# This is to generate api_secret and api_key for new user of erpnext
def generate_keys(user):

    user_details = frappe.get_doc('User', user)
    api_secret= frappe.generate_hash(length=15)
    api_key = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.save()
    print(api_key,"\n \n",api_secret)
    return api_secret, api_key

# This is to check otp validation
@frappe.whitelist(allow_guest=True)
def otp_checking(subject):
    print("this is otp_set_db")
    bq = frappe.db.get_value('OTP', subject, 'expiry_time')
    now1 = datetime.today()
    if bq==None:
            now = datetime.today()
            hour = now + timedelta(hours=24)
            chars = string.digits
            otp =  ''.join(choice(chars) for _ in range(4))
            frappe.db.set_value('OTP', subject, 'creation_time', now)
            frappe.db.set_value('OTP', subject, 'expiry_time', hour)
            frappe.db.set_value('OTP', subject, 'otp_creation', otp)
            frappe.db.commit()
            return otp
      
    elif now1>bq:
            now = datetime.today()
            hour = now + timedelta(hours=24)
            chars = string.digits
            otp =  ''.join(choice(chars) for _ in range(4))
            frappe.db.set_value('OTP', subject, 'creation_time', now)
            frappe.db.set_value('OTP', subject, 'expiry_time', hour)
            frappe.db.set_value('OTP', subject, 'otp_creation', otp)
            frappe.db.commit()
            return otp
    
    elif now1<bq:
            a = frappe.db.get_value('OTP', subject, 'otp_creation')
            return a


# This is to send otp 
# http://192.168.2.130:8022/api/method/android_app.apisend.login_otp_send
@frappe.whitelist(allow_guest=True)
def login_otp_send(usr):
    subject=frappe.db.exists("User", {'mobile_no': usr})
    if subject==None:
          return ("You are not Valid user of the system")
    else:
        otp = otp_checking(subject)  #Check otp timing
        otp_fetch_details(otp,usr)   #Send OTP
        return "You are valid User of system and OTP has been Sent"
    
# This is to allow user to use android app and generate sid and other required things
# GET http://192.168.2.130:8022/api/method/android_app.apisend.login
@frappe.whitelist(allow_guest=True)
def login(usr, otp, pwd="Sanskar"):
    otp_id=frappe.db.exists("OTP", {'android_user_mobile_no': usr,'otp_creation':otp})
    if otp_id==None:
        # return(otp_id,"You are Not permitted")
        return
    else:
        
        # print(otp_id,"You are Most Welcomed")
        try:
            login_manager = frappe.auth.LoginManager()
            login_manager.authenticate(user=usr, pwd=pwd)
            login_manager.post_login()
            driver = frappe.db.exists("Driver", {'cell_number': usr})
            user_id=frappe.db.exists("User", {'mobile_no': usr})
            # print(driver)
            # otp = otp_checking(user_id)  #Check otp timing
            # otp_fetch_details(otp,usr)   #Send OTP
        except frappe.exceptions.AuthenticationError:
            frappe.clear_messages()
            frappe.local.response["message"] = {
                "success_key":0,
                "message":"Authentication Error !"
            }
            return
        api_generate = generate_keys_login(frappe.session.user)
        user = frappe.get_doc('User', frappe.session.user)
        frappe.response["message"]={
            "success_key":1,
            "message":"Authentication Success !!",
            "sid":frappe.session.sid,
            "api_key":user.api_key,
            "api_secret":api_generate,
            "username":user.username,
            "mobile_no":user.mobile_no,
            "Driver": driver,
            "otp_id": otp_id,
            "user_id": user_id,
        }

# This is to generate api_secret for existing user of erpnext
def generate_keys_login(user):

    user_details = frappe.get_doc('User', user)
    api_secret= frappe.generate_hash(length=15)
    api_key = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.save()
    print(api_key,"\n \n",api_secret)
    return api_secret

# This is to know logged user
# http://192.168.2.130:8022/api/method/android_app.apisend.get_logged_user
@frappe.whitelist()
def get_logged_user():
    user = frappe.session.user
    frappe.local.response["message"]={
        "user": user,
    }
    return frappe.session.user

# this is for the driver details 
# http://192.168.2.130:8022/api/method/android_app.apisend.driver_info
@frappe.whitelist()
def driver_info(driver):
    return frappe.db.sql(f""" Select * from `tabDriver` where name='{driver}' """, as_dict=True)