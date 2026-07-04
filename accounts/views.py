from django.shortcuts import render

# Create your views here.
def homepage(request):
    return render(request,"accounts/home.html")

def login_page(request):
    return render(request,"accounts/login_page.html")

def register(request):
    return render(request,"accounts/register.html")