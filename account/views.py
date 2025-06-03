from django.shortcuts import render

# Create your views here.


def home(request):
    return render(request, "account/index.html")

def login(request):
    return render(request, "account/login.html")


def register(request):
    return render(request, "account/register.html")

