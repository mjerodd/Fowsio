import os.path
import socket
from netmiko import ConnectHandler, file_transfer, progress_bar
from netmiko.exceptions import NetmikoAuthenticationException
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from .church_firewall import ChurchFirewall
import jinja2
import os
import netaddr

jinja_temps = '/home/marv/PycharmProjects/Account_Template/starter/net_app/jinja_templates'

@shared_task(bind=True)
def fw_upgrade(self, fw_list, fw_ver):
    progress_recorder = ProgressRecorder(self)
    for fw in fw_list:
        print(fw)
        cf = ChurchFirewall(fw)
        cf.os_update(fw_ver)
        progress_recorder.set_progress(0 + 1, len(fw_list))


def conn_scan(tgt_host):
    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((str(tgt_host), 22))
        if sock:
            #print(str(tgt_host))
            sock.close()
            return str(tgt_host)
    except socket.timeout:
        print(f'[+] {tgt_host}/tcp ssh Closed')
    except OSError as e:
        print(f"Invalid IP: {e}")


@shared_task
def port_scan(tgt_ip):
    socket.setdefaulttimeout(1)
    tgt_ip = netaddr.IPNetwork(tgt_ip)
    output = [conn_scan(ip)for ip in tgt_ip]
    print(output)
    return output


def miko_connect(ip):
    try:
        dev = {
            'device_type': 'cisco_ios',
            'host': str(ip),
            'username': 'marv',
            'password': 'cisco',
        }

        net_connect = ConnectHandler(**dev)
        return net_connect

    except Exception as err:
        print(f"Failed login to {ip}")
        print(err)

def get_ints(dev_ip):
    net_connect = miko_connect(dev_ip)
    output = net_connect.send_command("show cdp neighbor", use_textfsm=True)
    print(output)
    for fact in output:

        if fact['platform'] == "IP Phone":
            continue
        neighbor = fact['neighbor']
        spl_neighbor = neighbor.split('.')
        neighbor = spl_neighbor[0]
        loc_int = fact['local_interface']
        rem_int = fact['neighbor_interface']
        net_connect.send_config_set([f"int {loc_int}", f"description {neighbor} - {rem_int}"])

@shared_task
def os_transfer(image, ip_list):
    try:
        for ip in ip_list:
            n_conn = miko_connect(ip)
            transfer = file_transfer(n_conn,
                                source_file=image,
                                dest_file = image,
                                file_system='flash:',
                                direction='put',
                                overwrite_file=True,
                                progress4=progress_bar)
            n_conn.disconnect()
            return transfer
    except OSError:
        print("File Transfer Completed")

def boot_new(image, ip):
    boot_comm = [
        'no boot system',
        f'boot system flash:{image}'
    ]
    net_connect = miko_connect(ip)
    net_connect.send_config_set(boot_comm)
    net_connect.send_command("wr mem")
    net_connect.send_command('reload', expect_string='confirm')
    net_connect.send_command('\n')



