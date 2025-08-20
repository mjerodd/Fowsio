import jinja2
from django.shortcuts import render, redirect
from .forms import NewRouterForm, NewSwitchForm, NewFirewallForm
from .models import Switch, Router, Firewall
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from .forms import CoreTempForm, IntDescriptionForm, IosUpgradeForm, PaloForm, PaloOsUpgradeForm, CoreSwitchConfForm
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command, netmiko_file_transfer
from nornir_utils.plugins.functions import print_result
from nornir_jinja2.plugins.tasks import template_file
from .church_firewall import ChurchFirewall
from .tasks import fw_upgrade, get_ints, port_scan
import zipfile
from io import BytesIO
# Create your views here.

def switches(request):
    form = NewSwitchForm()
    switches = Switch.objects.all()
    if request.method == 'POST':
        form = NewSwitchForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

    context = {'form': form, 'switches': switches}
    return render(request, "net_app/switches.html", context=context)

def switch_edit(request, slug):
    switch = Switch.objects.get(slug=slug)
    form = NewSwitchForm(request.POST or None, request.FILES or None, instance=switch)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('index')
    return render(request, 'net_app/switch_edit.html', {'form': form, 'switch': switch})

def routers(request):
    form = NewSwitchForm()
    routers = Router.objects.all()
    if request.method == 'POST':
        form = NewRouterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

    context = {'form': form, 'routers': routers}
    return render(request, "net_app/switches.html", context=context)

def router_edit(request, slug):
    router = Switch.objects.get(slug=slug)
    form = NewSwitchForm(request.POST or None, request.FILES or None, instance=router)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('index')
    return render(request, 'net_app/switch_edit.html', {'form': form, 'router': router})

def download_switch_templ(request, slug):
    switch = get_object_or_404(Switch, slug=slug)
    file_path = switch.template.path
    conv_file_path = str(switch.template)
    file_name = conv_file_path[25:]
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response

def index(request):
    return render(request, "net_app/index.html")


def os_trans(task):
    file_name = task.host.get('img')
    result = task.run(task=netmiko_file_transfer, source_file=file_name, dest_file=file_name, direction='put')
    return result


def send_to_switch(task):
    nr = InitNornir(
        config_file="/app/net_app/yaml_files/config.yaml")
    code_pres = task.run(task=netmiko_send_command, enable=True, command_string="dir flash: | in .bin")
    try:
        if '17.09.06a' in code_pres.result:
            print("No Need for File Transfer")
        else:
            vty_comm = ['line vty 0 15', 'exec-timeout 60']
            up_exec = task.run(task=netmiko_send_config, config_commands=vty_comm)
            print_result(up_exec)
            print(f"Starting Download For {task.host}")
            fin_result = nr.run(task=os_trans)
            print_result(fin_result)

    except OSError:
        print(f"File Transfer for {task.host} Complete")

def nex_conf(task):
    template = task.run(task=template_file, template="nx_template.j2", path="/app/net_app/yaml_files/config.yaml")
    task.host["stage_conf"] = template.result
    rendered = task.host["stage_conf"]
    configuration = rendered
    with open(f"{task.host}_conf.txt", "w") as f:
        f.write(configuration)

    task.run(task=netmiko_send_config, read_timeout=90, config_file=f"{task.host}_conf.txt")


def core_ip(subnet):
    ip_add = subnet
    split_ip = ip_add.split(".")
    vpc_oct = split_ip[2]
    split_ip[3] = "131"
    core1_ip = ".".join(split_ip)
    split_ip[3] = "132"
    core2_ip = ".".join(split_ip)
    split_ip[3] = "254"
    core_gw = ".".join(split_ip)
    return [core1_ip, core2_ip, core_gw, vpc_oct]


def core_temp(request):
    if request.method == 'POST':

        form = CoreSwitchConfForm(request.POST)

        if form.is_valid():
            print(form.cleaned_data)
            print(type(form.cleaned_data['subnet']))
            cor_ips = core_ip(form.cleaned_data['subnet'])
            switch1 = {
                "site_id" : form.cleaned_data['site_id'],
                "switch_num": "01",
                "mgmt_gw": cor_ips[2],
                "vpc_oct":cor_ips[3],
                "mgmt_ip": cor_ips[0],
                "logging_srv": form.cleaned_data['logging_srv'],
            }

            switch2 = {
                "site_id": form.cleaned_data['site_id'],
                "switch_num": "02",
                "mgmt_gw": cor_ips[2],
                "vpc_oct": cor_ips[3],
                "mgmt_ip": cor_ips[1],
                "logging_srv": form.cleaned_data['logging_srv'],
            }
            print(cor_ips)


            with open("./net_app/jinja_templates/nx_template.j2") as data:
                config = data.read()
            temp = jinja2.Template(config)
            switch1_conf = temp.render(switch1)
            switch2_conf = temp.render(switch2)

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add your text files to the zip
                zf.writestr(f'core05_{form.cleaned_data["site_id"]}_conf.txt', switch1_conf)
                zf.writestr(f'core06_{form.cleaned_data["site_id"]}_conf.txt', switch2_conf)

            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="text_files.zip"'
            return response

            '''
            response_sw1 = FileResponse(open(f"core01_{form.cleaned_data['site_id']}_conf.txt", 'rb'))
            response_sw2 = FileResponse(open(f"core01_{form.cleaned_data['site_id']}_conf.txt", 'rb'))
            response_sw1['Content-Type'] = 'application/octet-stream'
            response_sw1['Content-Disposition'] = f'attachment; filename="core01_conf"'
            response_sw2['Content-Type'] = 'application/octet-stream'
            response_sw2['Content-Disposition'] = f'attachment; filename="core01_conf"'
            return response_sw1
            '''

    form = CoreSwitchConfForm()
    context = {"form": form}
    return render(request, "net_app/core_build.html", context=context)


def thank_you(request):
    return render(request, "net_app/thanks.html")


def int_descriptions(request):
    if request.method == 'POST':
        form = IntDescriptionForm(request.POST)
        if form.is_valid():
            sub = form.cleaned_data['subnet']
            scan_list = port_scan.delay(sub)
            task_result = scan_list.get()
            for ip in task_result:
                if ip is not None:
                    print(ip)
                    get_ints(ip)
            return redirect("thank-you")
    else:
        form = IntDescriptionForm()
    return render(request, "net_app/int_description.html", {"form": form})


def ios_up(request):
    if request.method == 'POST':
        print('This is a post')

        nr = InitNornir(
            config_file="/app/net_app/yaml_files/config.yaml")
        results = nr.run(task=send_to_switch)
        print_result(results)
        #reload_result = nr.run(task=reboot)
        #OSError:
         #   print(f"File Transfer Complete")
        return redirect("thank-you")
    else:
        form = IosUpgradeForm()
        return render(request, "net_app/ios-upgrade.html", {"form": form})


def reboot(task):

    task.run(task=netmiko_send_config, enable=True, config_commands=['boot system flash:isr4300-universalk9.17.06.08a.SPA.bin'])

    task.run(task=netmiko_send_command, command_string='wr mem')
    task.run(task=netmiko_send_command, command_string='reload',  expect_string='confirm')
    task.run(task=netmiko_send_command, command_string='\n')


def ini_fw_auto(request):
    if request.method == 'POST':
        form = PaloForm(request.POST)

        if form.is_valid():
            print(form.cleaned_data)
            conf_fw = ChurchFirewall(form.cleaned_data['firewall_ip'])
            conf_fw.initial_clean()
            conf_fw.init_net(form.cleaned_data['wan_ip'])
            return redirect('index')
    else:
        form = PaloForm()
        context = {'form': form}
    return render(request, "net_app/firewall_auto.html", context=context)


def fw_os_auto(request):
    if request.method == 'POST':
        form = PaloOsUpgradeForm(request.POST)

        if form.is_valid():
            print("valid")
            print(form.cleaned_data)
            fw_ver = form.cleaned_data['version']
            #try:
            target = list(form.cleaned_data.values())[0]
            print(target)
            target_list = target.split(',')
            print(target_list)

            result = fw_upgrade.delay(target_list, fw_ver)

            #except Exception as e:
            #   print("Error: ", e)
            context = {'task_id': result.task_id}

            return render(request, "net_app/fw_os_auto.html", context)
    else:
        form = PaloOsUpgradeForm()
        context = {'form': form, 'task_id': None}
    return render(request, "net_app/fw_os_auto.html", context=context)


def fw_tools(request):
    return render(request, "net_app/fw_tools.html")

