from django.shortcuts import render, redirect
from .forms import NewRouterForm, NewSwitchForm, NewFirewallForm
from .models import Switch, Router, Firewall
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .forms import CoreTempForm, IntDescriptionForm, IosUpgradeForm, PaloForm, PaloOsUpgradeForm
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command, netmiko_file_transfer
from nornir_utils.plugins.functions import print_result
from nornir_jinja2.plugins.tasks import template_file
from .church_firewall import ChurchFirewall
from .tasks import fw_upgrade
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


def get_ints(task):
    cdp_result = task.run(task=netmiko_send_command, command_string="show cdp neighbor", use_textfsm=True)
    task.host["facts"] = cdp_result.result
    print(task.host["facts"])

    for fact in task.host["facts"]:
        if fact['platform'] == "IP Phone":
            continue
        neighbor = fact['neighbor']
        loc_int = fact['local_interface']
        rem_int = fact['neighbor_interface']
        task.run(task=netmiko_send_config, config_commands=[f"int {loc_int}", f"description {neighbor} - {rem_int}"])


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
    split_ip[3] = "31"
    core1_ip = ".".join(split_ip)
    split_ip[3] = "32"
    core2_ip = ".".join(split_ip)
    split_ip[3] = "254"
    core_gw = ".".join(split_ip)
    return [core1_ip, core2_ip, core_gw]


def core_temp(request):
    if request.method == 'POST':
        '''
        form = CoreTempForm(request.POST)

        if form.is_valid():
            print(form.cleaned_data)

            cor_ips = core_ip(form.cleaned_data['mgmt_subnet'])
            cores_dict[0]["data"]["mgmt_ip"] = cor_ips[0]
            cores_dict[1]["data"]["mgmt_ip"] = cor_ips[1]
            cores_dict[0]["data"]["mgmt_gw"] = cor_ips[2]
            cores_dict[1]["data"]["mgmt_gw"] = cor_ips[2]

            with open("./net_app/yaml_files/hosts6.yaml", "w") as f:
                yaml.dump(cores_dict, f)
            '''
        nr = InitNornir(
                config_file="/app/net_app/yaml_files/config.yaml")
        result = nr.run(task=nex_conf)
        print_result(result)
        return redirect("thank-you")
    else:
        form = CoreTempForm()
        context = {"form": form}
        return render(request, "net_app/core_build.html", context=context)


def thank_you(request):
    return render(request, "net_app/thanks.html")


def int_descriptions(request):
    if request.method == 'POST':
        nr = InitNornir(
            config_file="/app/net_app/yaml_files/config.yaml")
        result = nr.run(task=get_ints)
        print_result(result)
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

            fw_upgrade(target_list, fw_ver)

            #except Exception as e:
            #   print("Error: ", e)

            return redirect('index')
    else:
        form = PaloOsUpgradeForm()
        context = {'form': form}
    return render(request, "net_app/firewall_auto.html", context=context)


def fw_tools(request):
    return render(request, "net_app/fw_tools.html")