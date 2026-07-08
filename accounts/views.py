from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.db import transaction, IntegrityError
from django.contrib import messages
import random
from institution.models import Institution, InstitutionUser
from company.models import Company

# Create your views here.


def homepage(request):
    return render(request,"accounts/home.html")

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            if hasattr(user, 'institution_profile'):
                return redirect("institution:dashboard")
            elif hasattr(user, 'company'):
                return redirect("company:dashboard")
            else:
                
                return redirect("accounts:home")

        else:
            messages.error(request, "Invalid username or password.")
            return redirect("accounts:login_page")

    return render(request,"accounts/login_page.html")


def register(request):


    if request.method == "POST":
        user_type = request.POST.get("user_type")
        
        email = request.POST.get("email")
        username = request.POST.get("username")
        password = request.POST.get("password")

        if user_type == "institution":
            institution_name = request.POST.get("institution_name")
            phone_number = request.POST.get("phone_number")
            address = request.POST.get("address")

            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    
                    
                    institution = Institution.objects.create(
                        user=user, 
                        institution_name=institution_name,
                        phone_number=phone_number,
                        address=address,
                        email=email,
                    )
                    
                    InstitutionUser.objects.create(
                        user=user, institution=institution, role='admin'
                    )
                messages.success(request, "Institution account created successfully! Please log in.")
                return redirect("accounts:login_page")
            except IntegrityError:
                messages.error(request, "Username or email already exists.")

        elif user_type == "company":
            company_name = request.POST.get("company_name")
            phone_number = request.POST.get("phone_number")
            address = request.POST.get("address")

            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    Company.objects.create(
                        user=user,
                        company_name=company_name,
                        phone_number=phone_number,
                        address=address,
                        email=email,
                    )
                messages.success(request, "Company account created successfully! Please log in.")
                return redirect("accounts:login_page")
            except IntegrityError:
                messages.error(request, "Username or email already exists.")

    return render(request, "accounts/register.html")


def forget_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        otp = str(random.randint(100000, 999999))

        request.session["otp"] = otp
        request.session["email"] = email

        print("\n========================")
        print("EduPs Password Reset OTP")
        print("Email :", email)
        print("OTP   :", otp)
        print("========================\n")

        return redirect("accounts:verify_otp")

    return render(request, "accounts/forget_password.html")

def verify_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp")

        saved_otp = request.session.get("otp")

        if entered_otp == saved_otp:

            return redirect("accounts:reset_password")

    return render(request, "accounts/verify_otp.html")

def reset_password(request):
    return render(request, "accounts/reset_password.html")
