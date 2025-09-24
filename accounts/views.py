from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser, UserOTP
from .forms import SignupForm
from django.utils import timezone
from datetime import timedelta
from  django.contrib.auth import authenticate, login, logout
from .utils import success_notify, error_notify, warning_notify, info_notify



# Create your views here.

class SignupView(View):
    def get(self, request):
        form = SignupForm()
        return render(request, 'accounts/signup.html', {"form": form})
    
    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            otp = UserOTP.generate_otp()
            print("created otp is ", otp)
            UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
            
            # otp sending session
            html_content = render_to_string("emails/otp_signup.html", {"user": user, "otp": otp})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is {otp} ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()
            
            #checking the user is active or not
            emails = form.cleaned_data["email"]
            users = CustomUser.objects.get(email=emails)
            print("from signup user active", users.is_active)

            success_notify(request, "We sent you an OTP. Please verify your email.")
            
            return redirect("verify-otp", user_id=user.id)

            print("send email to user")
            return redirect("signin")
        return render(request, 'accounts/signup.html', {"form": form})
    
class VerifyOTPView(View):
    def get(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)
        return render(request, "accounts/verify_otp.html", {"user_id": user_id, "user": user})
    
    def post(self, request, user_id):
        entered_otp = request.POST.get("otp")
        user = CustomUser.objects.get(id=user_id)
        otp_obj = UserOTP.objects.get(user=user)

        if otp_obj.otp == entered_otp and otp_obj.created_at >=  timezone.now() - timedelta(minutes=5):
            print('user is active:', user.is_active)
            user.is_active = True
            user.save()
            otp_obj.delete()
            success_notify(request, "Your account has been verified. You can log in now.")
            return redirect("signin")
        else:
            otp_obj.delete()
            user.delete()
            return redirect("signup")

class ResendOTPView(View):
    def get(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)
        otp = UserOTP.generate_otp()
        print("resend otp is ", otp)
        print("full_name", user.full_name)
        UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})

        html_content = render_to_string("emails/otp_signup.html", {"user": user, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Resend OTP - Verify Your Account",
            body=f"Your new OTP is {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        success_notify(request, "A new OTP has been sent to your email.")
        return redirect("verify-otp", user_id=user.id)
        
    
class SigninView(View):

    def get(self, request):

        return render(request, 'accounts/signin.html')
    
    def post(self, request):
        emails = request.POST.get("email")
        passwords = request.POST.get("password")
        # users = CustomUser.objects.get(email=emails)

        if not emails:
            
            info_notify(request, "enter the mail")
            return redirect('signin')
        if not passwords:
            
            info_notify(request, "enter your password")
            return redirect('signin')
        

        user = authenticate(request, email=emails, password=passwords)
        # print("email is", emails)
        # print("password is ", passwords)
        # print("database email: ", user)
        # print("database password: ", user)
        # print("authenticated usser :",user.email)
        if user is not None:
            return redirect("cores-house", user_id=user.id)
        warning_notify(request, "invalid cridentials")
        # return redirect('signin')
    
class SignOutView(View):

    def get(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)

        if user.is_authenticated():

            return redirect('signin')
    def post(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)

        # if user.is_authenticated():
        return redirect('signin')
    

        