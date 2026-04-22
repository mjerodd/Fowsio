from panos import network, firewall, policies, ha, updater, device, objects
import xmltodict
from pprint import pprint
import subprocess, os, time, datetime, csv
import requests
from environ import Env


env = Env()
Env.read_env()



class ChurchFirewall:
    zones = ['zone_to-pa-hub', 'zone-to-hub', 'zone-to-branch', 'zone-internet', 'zone-internal', 'noc_transit_router',
             'noc_infrastructure_mgmt',
             'corp_wireless_mgmt', 'corp_casino_operations', 'corp_client_audiovisual', 'corp_client_general',
             'corp_client_pos', 'corp_client_utility',
             'corp_client_voip', 'corp_facility_general', 'corp_printer_general', 'internet_public', 'internet_open',
             'corp_server_casino', 'corp_server_general', 'corp_server_voip', 'corp_tracd nsit_router'
             ]

    fw_dict = {
        "fw_models": {
            "400 Series": {
                "ha1_a-int": "ethernet1/7",
                "ha1_b-int": None,
                "ha2-int": "ethernet1/8",
                "core-links": ['ethernet1/5', 'ethernet1/6'],
                "edge-links": ['ethernet1/1', 'ethernet1/2'],
            },
            "3400 Series": {
                "ha1_a-int": "ha1",
                "ha1_b-int": "ha1backup",
                "ha2-int": "ha2",
                "core-links": ['ethernet1/17', 'ethernet1/18'],
                "edge-links": ['ethernet1/19', 'ethernet1/20'],
            },
        }

    }

    def __init__(self, firewall_ip):
        self.api_user = "admin"
        self.api_password = "CRC_Derby"
        self.fw_host = firewall_ip
        self.fw_conn = firewall.Firewall(hostname=self.fw_host, api_username=self.api_user,
                                         api_password=self.api_password)
        self.fw_session = requests.Session()
        self.fw_token_response = self.fw_session.get(
            f'https://{firewall_ip}/api/?type=keygen&user={self.api_user}&password={self.api_password}',
            verify=False).text
        self.fw_token_dict = xmltodict.parse(self.fw_token_response)
        self.fw_token = self.fw_token_dict['response']['result']['key']

    def initial_clean(self):
        vwire = network.VirtualWire(name="default-vwire")
        self.fw_conn.add(vwire)
        vwire.delete()
        ruleb = policies.Rulebase()
        self.fw_conn.add(ruleb)
        del_rule = policies.SecurityRule(name="rule1")
        ruleb.add(del_rule)
        del_rule.delete()

        trust = network.Zone(name="trust")
        untrust = network.Zone(name="untrust")
        self.fw_conn.add(trust)
        self.fw_conn.add(untrust)
        trust.delete()
        untrust.delete()

        int_1 = network.EthernetInterface(name="ethernet1/4")
        int_2 = network.EthernetInterface(name="ethernet1/5")
        self.fw_conn.add(int_1)
        self.fw_conn.add(int_2)
        int_1.delete()
        int_2.delete()

        vr = network.VirtualRouter(name="default")
        self.fw_conn.add(vr)
        vr.delete()
        self.fw_conn.commit()

    def ha_setup(self, fw_model):
        model = fw_model
        ha_conf = ha.HighAvailability(enabled=True, group_id=10, state_sync=True, passive_link_state='auto',
                                      peer_ip='10.0.0.2', peer_ip_backup='10.0.0.6', ha2_keepalive=True)
        '''
        ha_eth1 = network.EthernetInterface("ethernet1/7", mode="ha")
        ha_eth2 = network.EthernetInterface("ethernet1/8", mode="ha")
        self.fw_conn.add(ha_eth1)
        self.fw_conn.add(ha_eth2)
        ha_eth1.create()
        ha_eth2.create()
        self.fw_conn.commit()
        '''

        ha1_int = ha.HA1("10.0.0.1", "255.255.255.252", port="ha1-a")
        ha1bu_int = ha.HA1Backup("10.0.0.5", "255.255.255.252", port="ha1-b")
        self.fw_conn.add(ha_conf)
        ha_conf.add(ha1_int)
        ha_conf.add(ha1bu_int)
        ha_conf.create()
        self.fw_conn.commit()


    def ha_link_monitor(self):
        url = f"https://{self.fw_host}/api"
        payload = f'key={self.fw_token}&type=config&action=set&xpath=%2Fconfig%2Fdevices%2Fentry%5B%40name%3D\'localhost.localdomain\'%5D%2Fdeviceconfig%2Fhigh-availability%2Fgroup%2Fmonitoring&element=%3Clink-monitoring%3E%0A%3Clink-group%3E%0A%3Centry%20name%3D%22Core_Switch_Links%22%3E%0A%3Cinterface%3E%0A%3Cmember%3Eethernet1%2F9%3C%2Fmember%3E%0A%3Cmember%3Eethernet1%2F10%3C%2Fmember%3E%0A%3C%2Finterface%3E%0A%3Cenabled%3Eyes%3C%2Fenabled%3E%0A%3C%2Fentry%3E%0A%3Centry%20name%3D%22Edge_Switch_Links%22%3E%0A%3Cinterface%3E%0A%3Cmember%3Eethernet1%2F19%3C%2Fmember%3E%0A%3Cmember%3Eethernet1%2F20%3C%2Fmember%3E%0A%3C%2Finterface%3E%0A%3Cenabled%3Eyes%3C%2Fenabled%3E%0A%3C%2Fentry%3E%0A%3C%2Flink-group%3E%0A%3Cenabled%3Eno%3C%2Fenabled%3E%0A%3C%2Flink-monitoring%3E%0A'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = self.fw_session.post(url, headers=headers, data=payload)

        print(response.text)


    def ping_fw(self):

        p_result = subprocess.run(['ping', '-c', '3', '-n', '192.168.1.11'], stdout=subprocess.PIPE, encoding='utf-8')
        loss = p_result.stdout.split('\n')[6]
        if '0% packet loss' in loss:
            print(loss)

    def set_mgmt(self):
        dev = device.SystemSettings(hostname='usMJT-fw01', ip_address='192.168.1.11', netmask='255.255.255.0',
                                    default_gateway='192.168.1.254',
                                    dns_primary='8.8.8.8', dns_secondary='8.8.8.1')
        self.fw_conn.add(dev)
        dev.create()
        self.fw_conn.commit()

    def create_sdwan_tags(self):
        #cc = objects.Tag.color_code('color26')
        sdwan_tag1 = objects.Tag(name='sdwan_inet_1', color='color26', comments='DIA Circuit 1')
        sdwan_tag2 = objects.Tag(name='sdwan_inet_2', color='color31', comments='DIA Circuit 2')
        self.fw_conn.add(sdwan_tag1)
        sdwan_tag1.create()
        self.fw_conn.add(sdwan_tag2)
        sdwan_tag2.create()
        self.fw_conn.commit()

    def sdwan_int_profile(self):
        self.create_sdwan_tags()
        url = f"https://{self.fw_host}/api"
        payload = f'key={self.fw_token}&type=config&action=set&xpath=%2Fconfig%2Fdevices%2Fentry%5B%40name%3D\'localhost.localdomain\'%5D%2Fvsys%2Fentry%5B%40name%3D\'vsys1\'%5D&element=%3Csdwan-interface-profile%3E%3Centry%20name%3D%22sdwan_dia_1%22%3E%3Clink-tag%3Esdwan_inet_1%3C%2Flink-tag%3E%3Clink-type%3EEthernet%3C%2Flink-type%3E%3Cpath-monitoring%3EAggressive%3C%2Fpath-monitoring%3E%3Cprobe-frequency%3E5%3C%2Fprobe-frequency%3E%3Cfailback-hold-time%3E120%3C%2Ffailback-hold-time%3E%3C%2Fentry%3E%3Centry%20name%3D%22sdwan_dia_2%22%3E%3Clink-tag%3Esdwan_inet_2%3C%2Flink-tag%3E%3Clink-type%3EEthernet%3C%2Flink-type%3E%3Cpath-monitoring%3EAggressive%3C%2Fpath-monitoring%3E%3Cprobe-frequency%3E5%3C%2Fprobe-frequency%3E%3Cfailback-hold-time%3E120%3C%2Ffailback-hold-time%3E%3C%2Fentry%3E%3C%2Fsdwan-interface-profile%3E'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = self.fw_session.post(url, headers=headers, data=payload)

        print(response.text)


    def disable_ztp(self):
        command = "set system ztp disable"
        self.fw_conn.op(cmd=command, xml=True)

        while True:
            time.sleep(60)
            if self.ping_fw() == False:
                break

        return "Firewall back online"

    def download_updates(self):

        updates = self.fw_conn.op(cmd='request content upgrade check', xml=True)
        format_update = xmltodict.parse(updates)
        update_list = format_update['response']['result']['content-updates']['entry']
        ver_list = []
        for vers in update_list:
            ver_num = vers['app-version'][-4:]
            ver_list.append(int(ver_num))

        new_ver = max(ver_list)
        print(new_ver)

        for i in update_list:
            if i['app-version'] in str(new_ver):
                print(f"Chose {i['app_version']}")
            '''
                downld_response = self.fw_conn.op(cmd='request content upgrade download latest', xml=True)
                dict_dwnld = xmltodict.parse(downld_response)
                print(dict_dwnld)
            '''

    def install_updates(self, filename):
        cmd = self.fw_session.get(
            f"https://{self.fw_host}/api/?type=op&cmd=<request><content><upgrade><install><file>{filename}</file></install></upgrade></content></request>&key={self.fw_token}",
            verify=False)
        form_install_resp = xmltodict.parse(cmd.text)
        pprint(form_install_resp)

        '''
        pprint(format_update['response']['result']['content-updates']['entry'], indent=3)


        info = self.fw_conn.op(cmd='request content upgrade info', xml=True)
        format_info = xmltodict.parse(info)
        pprint(format_info, indent=2)

        if updates.find('./result/updates-available/entry'):
            print("Downloading")

            print(info)
            self.fw_conn.op('request content upgrade download')
            self.fw_conn.op('request content upgrade install')
            self.fw_conn.commit()
        else:
            return None
    '''

    def enable_sdwan(self):
        sdwan_int = self.fw_conn.op(
            cmd='set network interface ethernet ethernet1/3 layer3 units ethernet1/1.1851 tag 1851', xml=True)
        dict_int = xmltodict.parse(sdwan_int)
        print(dict_int)

    def apply_bgp(self):

        url = f"https://{self.fw_host}/api"
        payload = f'key={self.fw_token}&type=config&action=set&xpath=%2Fconfig%2Fdevices%2Fentry%5B%40name%3D\'localhost.localdomain\'%5D%2Fnetwork%2Fvirtual-router%2Fentry%5B%40name%3D\'sdwan\'%5D%2Fprotocol&element=%3Cbgp%3E%3Crouting-options%3E%3Cgraceful-restart%3E%3Cenable%3Eyes%3C%2Fenable%3E%3C%2Fgraceful-restart%3E%3Cas-format%3E4-byte%3C%2Fas-format%3E%3C%2Frouting-options%3E%3Cenable%3Eyes%3C%2Fenable%3E%3Crouter-id%3E100.64.10.1%3C%2Frouter-id%3E%3Clocal-as%3E63415%3C%2Flocal-as%3E%3C%2Fbgp%3E%0A'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response = self.fw_session.post(url, headers=headers, data=payload)

        print(response.text)

    def create_zone(self, zone):
        add_zone = network.Zone(name=zone, mode="layer3")
        self.fw_conn.add(add_zone)
        add_zone.create()

    def init_net(self):
        vr = network.VirtualRouter(name='sdwan')
        self.fw_conn.add(vr)
        vr.create()

        agg_int = network.AggregateInterface(name='ae1', mode='layer3', lacp_enable=True, lacp_mode='active',
                                             lacp_rate='slow')
        self.fw_conn.add(agg_int)
        agg_int.create()

        for zone in self.zones:
            self.create_zone(zone)
        self.fw_conn.commit()

        phys_int = network.EthernetInterface(name='ethernet1/5', mode='aggregate-group', aggregate_group='ae1')
        self.fw_conn.add(phys_int)
        phys_int.create()

        wan_phy_int = network.EthernetInterface(name='ethernet1/3', mode='layer3', lldp_enabled=True, enable_dhcp=True)
        self.fw_conn.add(wan_phy_int)
        wan_phy_int.create()

        wan_sub_int = network.Layer3Subinterface('ethernet1/3.1851', tag=1851, ip=('6.6.5.1/29',))
        self.fw_conn.add(wan_sub_int)
        wan_sub_int.create()
        wan_sub_int.set_zone('internet_public', update=True, running_config=True)
        wan_sub_int.set_virtual_router('sdwan', update=True, running_config=True)

        self.fw_conn.commit()

    def os_update(self, version):
        code = updater.SoftwareUpdater(self.fw_conn)
        code.download_install_reboot(version=version)
        # once program completes device reboots

    def disable_pan2(self):
        pan2 = device.SystemSettings(panorama2="1.1.1.1")
        self.fw_conn.add(pan2)
        pan2.delete()
        self.fw_conn.commit()

    def content_update(self):
        cont = updater.ContentUpdater(self.fw_conn)
        cont.download_install(version='latest')

    def get_cdi_dhcp(self):

        decom_ip = ["172.17.35.2", "172.17.64.23", "172.16.67.4", "172.16.32.100", "172.16.98.130", "172.17.130.19",
                    "172.17.226.100", "172.16.147.5", "172.17.176.12", "172.17.160.231", "172.16.4.20", "172.16.115.5",
                    "172.17.234.100", "172.16.131.14", "172.16.9.219", "172.17.254.2", "172.16.4.21", "172.16.9.220",
                    "172.16.9.10", "172.16.9.150", "172.16.4.21", "172.17.160.230", "172.16.4.25", "172.16.9.130", "172.16.9.241",
                    "172.16.4.233", "172.16.4.245", "172.16.4.232", "172.16.4.231"]

        dhcp_info = self.fw_conn.op('show dhcp server settings "all"', xml=True)
        dict_dhcp = xmltodict.parse(dhcp_info)
        dhcp_list = dict_dhcp['response']['result']['entry']
        for entry in dhcp_list:
            print(f"FW - {self.fw_host}\tInterface: {entry['@name']}")
            print("********************************************************")
            print(f"Primary DNS: {entry['dns1']}")
            print(f"Secondary DNS: {entry['dns2']}")
            print("********************************************************\n")
            if entry['dns1'] or entry['dns2'] in decom_ip:
                print(f"[*] Invalid DNS detected on {self.fw_host} {entry['@name']}")

    def get_dns(self):
        # url = "https://192.168.1.11/api?type=config&action=get&xpath=/config/devices/entry[@name='localhost.localdomain']/deviceconfig/system/dns-setting/servers&key=LUFRPT1YSGlOMCtYQUxZMEp1VGZGUEZyV1NxMXhvaTA9blRQTkY2a21Rc2VYVkh6UTZ6bTlCdHg5d2JNSkVPaXYxT0ROc0VkODFTdCtoa3RmSW1TTi94TG12Nk50ZlBZTQ=="
        response = self.fw_session.get(
            f"https://{self.fw_host}/api?type=config&action=get&xpath=/config/devices/entry[@name='localhost.localdomain']/deviceconfig/system/dns-setting/servers&key={self.fw_token}",
            verify=False)
        dict_response = xmltodict.parse(response.text)
        l1_dict_resp = dict_response['response']['result']['servers']

        return l1_dict_resp

    def get_ntp(self):
        ntp_servers = {}
        response = self.fw_session.get(
            f"https://{self.fw_host}/api?type=config&action=get&xpath=/config/devices/entry[@name='localhost.localdomain']/deviceconfig/system/ntp-servers&key={self.fw_token}",
            verify=False)

        dict_response = xmltodict.parse(response.text)
        ntp_servers['pri_ntp'] = \
        dict_response['response']['result']['ntp-servers']['primary-ntp-server']['ntp-server-address']['#text']
        ntp_servers['sec_ntp'] = \
        dict_response['response']['result']['ntp-servers']['secondary-ntp-server']['ntp-server-address']['#text']
        return ntp_servers

    def sip_alg(self):

        url = f"https://{self.fw_host}/api/?type=config&action=get&xpath=/config/shared/alg-override/application/entry[@name='sip']"

        headers = {

            'X-PAN-KEY': self.fw_token,

        }

        response = requests.request("GET", url, headers=headers, verify=False)

        dict_response = xmltodict.parse(response.text)

        pprint(dict_response)

        if dict_response['response']['result'] == None:

            ans = "Not Disabled"

        elif dict_response['response']['result']['entry']['alg-disabled'] == 'no':

            ans = "Enabled"

            sip_ans = dict_response['response']['result']['entry']

            pprint(sip_ans)

        else:

            ans = "Disabled"

            sip_ans = dict_response['response']['result']['entry']

            pprint(sip_ans)

        return ans

    def fw_csv(self, sip_alg_enabled, version, hostname, timezone, p_dns, s_dns, p_ntp, s_ntp, pano_ip, ha_enabled,

               ha_core_lm_ena, ha_core_lm_int1, ha_core_lm_int1_stat, ha_core_lm_int2, ha_core_lm_int2_stat,

               ha_wan_lm_ena, ha_wan_lm_int1, ha_wan_lm_int1_stat, ha_wan_lm_int2, ha_wan_lm_int2_stat, ha_ha1_ip,

               ha_ha1_bu_ip, ha_preempt, ha_priority, ha_ha1_conn, ha_ha1_bu_conn, ha_ha2_conn, ha_ha1_peer_ip,

               ha_ha1_peer_bu_ip, admin_user_pres):

        with open(f"fw_checklist_{datetime.datetime.now()}", 'w', newline='') as cv:
            writer = csv.writer(cv)

            (writer.writerow(['Hostname', 'FW IP', 'SIP ALG Status', 'Software Version', 'Timezone',

                              'Primary DNS', 'Secondary DNS', 'Primary NTP', 'Secondary NTP', 'Panorama IP',
                              'HA Enabled',

                              'HA Core Link Monitoring', 'HA Core Monitoring Int 1', 'HA Core Monitoring Int 2',
                              'HA WAN Link Monitoring',

                              'HA WAN Monitoring Int 1', 'HA WAN Monitoring Int 2', 'HA1 IP', 'HA1 Backup IP',
                              'HA Preempt',

                              'HA Priority', 'HA1 Connection Status', 'HA1 BU Connection Status',
                              'HA2 Connection Status',

                              'HA1 Peer IP', 'HA1 Peer BU IP', 'Admin User Present']))

            writer.writerow(
                [hostname, self.fw_host, sip_alg_enabled, version, timezone, p_dns, s_dns, p_ntp, s_ntp, pano_ip,
                 ha_enabled,

                 ha_core_lm_ena, ha_core_lm_int1 + ' : ' + ha_core_lm_int1_stat,
                 ha_core_lm_int2 + ' : ' + ha_core_lm_int2_stat,

                 ha_wan_lm_ena, ha_wan_lm_int1 + ' : ' + ha_wan_lm_int1_stat,
                 ha_wan_lm_int2 + ' : ' + ha_wan_lm_int2_stat,

                 ha_ha1_ip, ha_ha1_bu_ip, ha_preempt, ha_priority, ha_ha1_conn, ha_ha1_bu_conn, ha_ha2_conn,

                 ha_ha1_peer_ip, ha_ha1_peer_bu_ip, admin_user_pres])

    def all_fw_dict(self):

        pano = Panorama(hostname="10.32.15.7", api_username="m.thomas", api_password="Marvelou5marv77^")

        # pprint(dir(pano))

        devs = pano.refresh_devices(expand_vsys=False)

        cdi_fw_dict = {}

        for fw in devs:

            if fw:

                try:

                    system = fw.find("", SystemSettings)

                    # print(f"{system.hostname} {system.ip_address}")

                    cdi_fw_dict[system.hostname] = system.ip_address

                except AttributeError as e:

                    print(e)

        return cdi_fw_dict

    def ha_status(self):

        ha_results = self.fw_conn.op(cmd='show high-availability all', xml=True)

        results_dict = xmltodict.parse(ha_results)

        pprint(results_dict)

        try:

            ha_enabled = results_dict['response']['result']['enabled']

        except Exception as err:

            print(f"There are problems with HA being enabled for {self.fw_host}, {err}")

            ha_enabled = "Null"

        try:

            ha_core_lm_ena = results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][0][
                'enabled']

        except Exception as err:

            print(f"There are problems with HA Link Monitoring being enabled for {self.fw_host}, {err}")

            ha_core_lm_ena = "Null"

        try:

            ha_core_lm_int1 = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][0]['interface']['entry'][
                0]['name']

        except Exception as err:

            print(f"There are problems with HA Link Monitoring for {self.fw_host}, {err}")

            ha_core_lm_int1 = "Null"

        try:

            ha_core_lm_int1_stat = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][0]['interface']['entry'][
                0]['status']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_core_lm_int1_stat = "Null"

        try:

            ha_core_lm_int2 = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][0]['interface']['entry'][
                1]['name']

        except Exception as err:

            print(f"There are problems with HA link monitoring for {self.fw_host}, {err}")

            ha_core_lm_int2 = "Null"

        try:

            ha_core_lm_int2_stat = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][0]['interface']['entry'][
                1]['status']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_core_lm_int2_stat = "Null"

        try:

            ha_wan_lm_ena = results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][1][
                'enabled']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_wan_lm_ena = "Null"

        try:

            ha_wan_lm_int1 = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][1]['interface']['entry'][
                0]['name']

        except Exception as err:

            print(f"There are problems with HA link monitoring for {self.fw_host}, {err}")

            ha_wan_lm_int1 = "Null"

        try:

            ha_wan_lm_int1_stat = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][1]['interface']['entry'][
                0]['status']

        except Exception as err:

            print(f"There are problems with HA link monitoring for {self.fw_host}, {err}")

            ha_wan_lm_int1_stat = "Null"

        try:

            ha_wan_lm_int2 = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][1]['interface']['entry'][
                1]['name']

        except Exception as err:

            print(f"There are problems with HA link monitoring for {self.fw_host}, {err}")

            ha_wan_lm_int2 = "Null"

        try:

            ha_wan_lm_int2_stat = \
            results_dict['response']['result']['group']['link-monitoring']['groups']['entry'][1]['interface']['entry'][
                1]['status']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_wan_lm_int2_stat = "Null"

        try:

            ha_ha1_ip = results_dict['response']['result']['group']['local-info']['ha1-ipaddr']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_ha1_ip = "Null"

        try:

            ha_ha1_bu_ip = results_dict['response']['result']['group']['local-info']['ha1-backup-ipaddr']

        except Exception as err:

            print(f"There are problems with HA link monitoring status for {self.fw_host}, {err}")

            ha_ha1_bu_ip = "Null"

        try:

            ha_preempt = results_dict['response']['result']['group']['local-info']['preemptive']

        except Exception as err:

            print(f"There are problems with HA preemption for {self.fw_host}, {err}")

            ha_preempt = "Null"

        try:

            ha_priority = results_dict['response']['result']['group']['local-info']['priority']

        except Exception as err:

            print(f"There are problems with HA priority for {self.fw_host}, {err}")

            ha_priority = "Null"

        try:

            ha_ha1_conn = results_dict['response']['result']['group']['peer-info']['conn-ha1']['conn-status']

        except Exception as err:

            print(f"There are problems with HA1 connectin status for {self.fw_host}, {err}")

            ha_ha1_conn = "Null"

        try:

            ha_ha1_bu_conn = results_dict['response']['result']['group']['peer-info']['conn-ha1-backup']['conn-status']

        except Exception as err:

            print(f"There are problems with HA1 backup connection status for {self.fw_host}, {err}")

            ha_ha1_bu_conn = "Null"

        try:

            ha_ha2_conn = results_dict['response']['result']['group']['peer-info']['conn-ha2']['conn-status']

        except Exception as err:

            print(f"There are problems with HA2 connection status for {self.fw_host}, {err}")

            ha_ha2_conn = "Null"

        try:

            ha_ha1_peer_ip = results_dict['response']['result']['group']['peer-info']['ha1-ipaddr']

        except Exception as err:

            print(f"There are problems with HA2 connection status for {self.fw_host}, {err}")

            ha_ha1_peer_ip = "Null"

        try:

            ha_ha1_peer_bu_ip = results_dict['response']['result']['group']['peer-info']['ha1-backup-ipaddr']

        except Exception as err:

            print(f"There are problems with HA1 peer backup ip for {self.fw_host}, {err}")

            ha_ha1_peer_bu_ip = "Null"

        ha_list = [ha_enabled, ha_core_lm_ena, (ha_core_lm_int1, ha_core_lm_int1_stat),

                   (ha_core_lm_int2, ha_core_lm_int2_stat), ha_wan_lm_ena, (ha_wan_lm_int1, ha_wan_lm_int1_stat),

                   (ha_wan_lm_int2, ha_wan_lm_int2_stat),

                   ha_ha1_ip, ha_ha1_bu_ip, ha_preempt, ha_priority, ha_ha1_conn, ha_ha1_bu_conn, ha_ha2_conn,

                   ha_ha1_peer_ip, ha_ha1_peer_bu_ip]

        print(ha_list)

        return ha_list

    def fw_sys_info(self):

        sys_info_list = []

        sys_results = self.fw_conn.op(cmd='show system info', xml=True)

        fw_tz = self.fw_conn.op(cmd='show clock', xml=True)

        pano = self.fw_conn.op(cmd='show panorama-status', xml=True)

        results_dict = xmltodict.parse(sys_results)

        tz_dict = xmltodict.parse(fw_tz)

        timezone = tz_dict['response']['result'].split(' ')[4]

        soft_ver = results_dict['response']['result']['system']['sw-version']

        fw_hostname = results_dict['response']['result']['system']['devicename']

        pano_dict = xmltodict.parse(pano)

        pano_ip = pano_dict['response']['result'].split(':')[1][1:14]

        sys_info_list.append(soft_ver)

        sys_info_list.append(fw_hostname)

        sys_info_list.append(timezone)

        sys_info_list.append(pano_ip)

        print(sys_info_list)

        return sys_info_list

    def get_users(self):

        response = self.fw_session.get(
            f"https://{self.fw_host}/api?type=config&action=get&xpath=/config/mgt-config/users&key={self.fw_token}",
            verify=False)

        dict_response = xmltodict.parse(response.text)

        # pprint(dict_response)

        user_list = dict_response['response']['result']['users']['entry']

        if isinstance(user_list, dict):

            if user_list['@name'] == 'admin':
                return 'remove admin user'

        for user in user_list:

            if 'admin' in user['@name']:

                if user['@name'] != 'cdiadmin':
                    return 'remove admin user'

            else:

                return 'no'