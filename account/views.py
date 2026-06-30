from multiprocessing import context
from multiprocessing.context import AuthenticationError

from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from .forms import CreateUserForm
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Create your views here.


@login_required(login_url='login')
def home(request):
    return render(request, "account/index.html")

def my_login(request):
    form = AuthenticationForm()
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')

    context = {'form': form}
    return render(request, "account/login.html", context)


def register(request):
    form = CreateUserForm()
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    context = {
        'form': form,
    }
    return render(request, "account/register.html", context)

def user_logout(request):
    logout(request)
    return redirect('login')