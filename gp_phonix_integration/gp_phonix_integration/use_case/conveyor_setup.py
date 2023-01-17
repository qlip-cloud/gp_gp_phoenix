import frappe
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import SYNCONVENYOR

DAYS_OF_WEEKS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday"
]

TIME_DEFAULT = '23:59:59'

@frappe.whitelist()
def sync_conveyor(master_name):

    master_setup = get_master_setup(master_name)

    conveyor_list = get_conveyor_list(master_setup.company)

    sync_response = add_or_update_conveyor(conveyor_list)

    frappe.log_error(sync_response, title="Sync Result")

    return sync_response


def get_conveyor_list(company):

    conveyor_respose = execute_send(company_name = company, endpoint_code = SYNCONVENYOR)

    return conveyor_respose.get("Conveyors")


def add_or_update_conveyor(conveyor_list):

    count_conveyor_add = 0

    count_conveyor_update = 0

    for conveyor_iter in conveyor_list:

        if not frappe.db.exists("qp_GP_ShippingType", {"shipment_method": conveyor_iter.get("ShipmentMethod")}):

            create_conveyor(conveyor_iter)

            count_conveyor_add += 1
        else:

            update_conveyor(conveyor_iter)

            count_conveyor_update+= 1

    return {
        'total_conveyor': len(conveyor_list),
        'count_conveyor_add': count_conveyor_add,
        'count_conveyor_update': count_conveyor_update
    }


def create_conveyor(conveyor_iter):

    conveyor = frappe.new_doc("qp_GP_ShippingType")

    conveyor.shipment_method = conveyor_iter.get("ShipmentMethod")

    conveyor.conveyor = conveyor_iter.get("Conveyor")

    for day_of_week in DAYS_OF_WEEKS:

        dow_obj = __create_weekly_schedule_object(
            day_of_week,
            conveyor_iter.get(day_of_week))

        conveyor.append('weekly_schedule', dow_obj)

    conveyor.save()


def update_conveyor(conveyor_iter):

    conveyor = frappe.get_doc('qp_GP_ShippingType', conveyor_iter.get("ShipmentMethod"))

    reg_db = [weekly_schedule.day for weekly_schedule in conveyor.weekly_schedule]

    reg_add = list(set(DAYS_OF_WEEKS) - set(reg_db))

    reg_upd = list(set(DAYS_OF_WEEKS) & set(reg_db))

    for weekly_schedule in conveyor.weekly_schedule:

        if weekly_schedule.day in reg_upd:

            weekly_schedule.enabled = conveyor_iter.get(weekly_schedule.day)

            if weekly_schedule.enabled == '0':

                weekly_schedule.delivery_time = TIME_DEFAULT.format("HH:mm:ss")

                weekly_schedule.cut_off = 0

    for iter_day in reg_add:

        dow_obj = __create_weekly_schedule_object(
            iter_day,
            conveyor_iter.get(iter_day))

        conveyor.append('weekly_schedule', dow_obj)

    conveyor.save()


def __create_weekly_schedule_object(day_of_week, value):

    return {
        'day': day_of_week,
        'enabled': value,
        'delivery_time': TIME_DEFAULT.format("HH:mm:ss")
    }

