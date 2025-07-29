from celery import shared_task
from .church_firewall import ChurchFirewall


@shared_task
def fw_upgrade(fw_list, fw_ver):
    for fw in fw_list:
        print(fw)
        cf = ChurchFirewall(fw)
        cf.os_update(fw_ver)

@shared_task
def task2():
    return