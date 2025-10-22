from django.shortcuts import render, redirect, get_object_or_404
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
from django.views.decorators.cache import never_cache, cache_control
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


# Create your views here.
@method_decorator(never_cache, name='dispatch')
class SignupView(View):
    
    def get(self, request):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        # if request.session.get("signup_done"):
        #     return redirect("verify-otp", user_id=request.user.id)
        
        form = SignupForm()
        return render(request, 'accounts/signup1.html', {"form": form})
    
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
            # users = CustomUser.objects.get(email=emails)# add get_object_or_404
            users = get_object_or_404(CustomUser, email=emails)
            print("from signup user active", users.is_active)

            # destroying previous session
            request.session.pop("otp_verified", None)

            success_notify(request, "We sent you an OTP. Please verify your email.")
            
            return redirect("verify-otp", user_id=user.id)

            
        return render(request, 'accounts/signup.html', {"form": form})
    
@method_decorator(never_cache, name='dispatch')
class VerifyOTPView(View):
    def get(self, request, user_id):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        # if not request.session.get("signup_done"):

        #     return redirect("signup") 

        if request.session.get("otp_verified"):

            return redirect("signin")
        
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        
        
        return render(request, "accounts/verify_otp.html", {"user_id": user_id, "user": user})
    
    def post(self, request, user_id):
        entered_otp = request.POST.get("otp")
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        # otp_obj = UserOTP.objects.get(user=user)# add get_object_or_404
        otp_obj = get_object_or_404(UserOTP, user=user)


        if not entered_otp:
            error_notify(request, "enter your otp")
            return redirect('verify-otp', user_id=user.id)

        if otp_obj.otp == entered_otp and otp_obj.created_at >=  timezone.now() - timedelta(minutes=5):
            print('user is active:', user.is_active)
            user.is_active = True
            user.save()

            # make session and clear previos session
            # request.session.pop("signup_done", None)
            request.session["otp_verified"] = True

            otp_obj.delete()
            success_notify(request, "Your account has been verified. You can log in now.")
            return redirect("signin")
        else:
            otp_obj.delete()
            user.delete()
            return redirect("signup")
        
@method_decorator(never_cache, name='dispatch')
class ResendOTPView(View):
    def get(self, request, user_id):
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        otp = UserOTP.generate_otp()
        print("resend otp is ", otp)
        print("full_name", user.full_name)
        UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
        
        
        html_content = render_to_string("emails/otp_signup.html", {"user": user, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Resend OTP - Verify Your Account",
            body=f"Your new OTP is {otp}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        
        
        success_notify(request, "A new OTP has been sent to your email.")
        return redirect("verify-otp", user_id=user.id)
        
    
@method_decorator(never_cache, name='dispatch')
class SigninView(View):

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            


        # if request.session.get("otp_verified"):
        #     return redirect("sig")
        
        return render(request, 'accounts/signin1.html')
    
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
        # user1 = CustomUser.objects.get(email=emails)
        user = authenticate(request, email=emails, password=passwords)
        
        print("email is", emails)
        print("password is ", passwords)
        print(" usser is authenticated :",user)
        if user is not None:
            user.status = True
            print("user satus ", user.status)
            if user.is_superuser:
                request.session.pop("otp_verified", None)
                login(request, user)
                
                
                return redirect('admin-dash', user_id= user.id)
            else:
                request.session.pop("otp_verified", None)
                login(request, user)
                
                
                return redirect("cores-home", user_id=user.id)
        warning_notify(request, "invalid cridentials")
        return redirect('signin')
    


class SignOutView(View):

    def get(self, request, user_id):

        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        logout(request)
        user.status = False
        print("user status:",user.status)
        

        return redirect('signin')
    def post(self, request, user_id):
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        
        logout(request)
        user.status = False
        print("user status:",user.status)

        # if user.is_authenticated():
        return redirect('signin')
    
@method_decorator(never_cache, name='dispatch')
@method_decorator(cache_control(no_cache=True, no_store=True, must_revalidate=True), name='dispatch')

class ForgotPassView(View):

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        # if request.session.get("forgot_otp_verified"):

        #     return render(request, '')
            
        return render(request, 'accounts/forgotpass.html')
    
    def post(self, request):

        email = request.POST.get('email')


        


        if not CustomUser.objects.filter(email=email).exists():
            error_notify(request, 'thre is no account use this email')
            return redirect('forgot_pass')
        
        user = get_object_or_404(CustomUser, email=email)
        
        otp = UserOTP.generate_otp()
        print("created otp is ", otp)
        UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
            
        # otp sending session
        html_content = render_to_string("emails/otp_forgot.html", {"user": user, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Verify Your Account",
            body=f"Your OTP is {otp} ",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send()

        success_notify(request, "We sent you an OTP. Please verify your email.")
        # return redirect('forgot_pass')
            
        return redirect("verify_forgot_otp", user_id=user.id)
    
@method_decorator(never_cache, name='dispatch')
class VerifyForgotOTPView(View):
    def get(self, request, user_id):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        # if not request.session.get("signup_done"):

        #     return redirect("signup") 

        # forgot otp session check
        
        if request.session.get("forgot_otp_verified"):

            return redirect('new_pass', user_id=user_id)
        
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        
        
        return render(request, "accounts/verify_forgot_otp.html", {"user_id": user_id, "user": user})
    
    def post(self, request, user_id):
        entered_otp = request.POST.get("otp")
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        # otp_obj = UserOTP.objects.get(user=user)# add get_object_or_404
        otp_obj = get_object_or_404(UserOTP, user=user)


        if not entered_otp:
            error_notify(request, "check your email and enter your otp")
            return redirect('verify_forgot_otp', user_id=user.id)

        if otp_obj.otp == entered_otp and otp_obj.created_at >=  timezone.now() - timedelta(minutes=5):
            print('user is active:', user.is_active)
            
            

            # make session and clear previos session
            # request.session.pop("signup_done", None)
            request.session["forgot_otp_verified"] = True

            otp_obj.delete()
            success_notify(request, "Your account has been verified. You can create new password now.")
            return redirect("new_pass", user_id=user.id)
        else:
            otp_obj.delete()
            warning_notify(request, "your otp validity is over enter your mail again")
            return redirect("forgot_pass")
        
@method_decorator(never_cache, name='dispatch')
class ResendPasswordOTPView(View):
    def get(self, request, user_id):
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        otp = UserOTP.generate_otp()
        print("resend otp is ", otp)
        print("full_name", user.full_name)
        UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
        
        
        html_content = render_to_string("emails/otp_forgot.html", {"user": user, "otp": otp})
        
        email = EmailMultiAlternatives(
            subject="Resend OTP - Verify Your Account",
            body=f"Your new OTP is {otp}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        
        
        success_notify(request, "A new OTP has been sent to your email.")
        return redirect("verify_forgot_otp", user_id=user.id)
    

@method_decorator(never_cache, name='dispatch')        
class ResetPasswordView(View):

    def get(self, request, user_id):

        user = get_object_or_404(CustomUser, id=user_id)
        return render(request, 'accounts/newpass.html', {"user_id": user_id, "user": user})
    
    def post(self, request, user_id):

        password = request.POST.get('password')
        confirm_pass = request.POST.get('confirm_password')

        user = get_object_or_404(CustomUser, id=user_id)

        if not password:
            error_notify(request, 'enter your password')
            return redirect('new_pass', user_id=user_id)
        if not confirm_pass:
            error_notify(request, 'enter your password')
            return redirect('new_pass', user_id=user_id)
        if password != confirm_pass:
            error_notify(request, 'The password entered does not match.')
            return redirect('new_pass', user_id=user_id)
        
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            # e.messages is list of strings
            for msg in e.messages:
                error_notify(request, msg)
            return redirect('new_pass', user_id=user_id)
        

        user.set_password(password)
        user.save()
        request.session.pop("forgot_otp_verified", None)
        success_notify(request, "Your password has been changed successfully.")
        return redirect('signin')