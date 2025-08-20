from django import forms
from .models import Router, Switch, Firewall

class NewRouterForm(forms.ModelForm):

    class Meta:

        model = Router
        fields = ['vendor', 'role', 'model', 'template']


class NewSwitchForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].widget.attrs.update({
                                                      'class': "shadow-md bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-xs-light"})
        self.fields["role"].widget.attrs.update({
                                                    'class': "shadow-md bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-xs-light"})
        self.fields["model"].widget.attrs.update({
                                                     'class': "shadow-md bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-xs-light"})
        self.fields["template"].widget.attrs.update({
                                                        'class': "shadow-md bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 dark:shadow-xs-light"})

    class Meta:

        model = Switch
        fields = ['vendor', 'role', 'model', 'template']


class NewFirewallForm(forms.ModelForm):
    class Meta:
        model = Switch
        fields = ['vendor', 'role', 'model', 'template']


class CoreTempForm(forms.Form):
    site_id = forms.CharField()
    mgmt_subnet = forms.CharField()


class IntDescriptionForm(forms.Form):
    site_id = forms.CharField()
    subnet = forms.CharField(max_length=30)


class IosUpgradeForm(forms.Form):
    site_id = forms.CharField()


class PaloForm(forms.Form):
    firewall_ip = forms.GenericIPAddressField(label="Firewall IP")
    wan_ip = forms.CharField(max_length=30)


class PaloOsUpgradeForm(forms.Form):
    firewall_ip = forms.CharField(label="Enter each IP to be upgraded", widget=forms.Textarea)
    version = forms.CharField(max_length=20, label="Code Version")

class CoreSwitchConfForm(forms.Form):
    subnet = forms.CharField(max_length=20, label="Site Mgmt subnet")
    site_id = forms.CharField(max_length=3)
    logging_srv = forms.CharField(max_length=20, label="Site Logging Server")