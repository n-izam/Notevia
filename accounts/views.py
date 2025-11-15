from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser, UserOTP, UserProfile, Address, SignUpUserOTP
from .forms import SignupForm, SigninForm
from django.utils import timezone
from datetime import timedelta
from  django.contrib.auth import authenticate, login, logout
from .utils import success_notify, error_notify, warning_notify, info_notify, referral_amount, profile
from django.views.decorators.cache import never_cache, cache_control
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from cloudinary.uploader import destroy
import re
from products.models import Referral, Wishlist
from cart.models import Wallet
from decimal import Decimal
from django.contrib.auth.decorators import login_required


# Create your views here.
@method_decorator(never_cache, name='dispatch')
class SignupView(View):
    
    def get(self, request):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        if request.session.get('user_email'):
            del request.session['user_email']
            del request.session['user_full_name']
            del request.session['user_phone_no']
            del request.session['user_password']
            return redirect('signup')
    

        # this is important because chaange password safety
        if request.session.get("forgot_otp_verified"):
            request.session.pop("forgot_otp_verified", None)
        
        form = SignupForm()
        return render(request, 'accounts/signup1.html', {"form": form})
    
    def post(self, request):
        referel_code = request.POST.get('referrel')
        if referel_code:
            if not Referral.objects.filter(code=referel_code).exists():
                error_notify(request, 'wrong referral, try again')
                return redirect('signup')
            else:
                request.session['referral_code'] = referel_code
                print(request.session.get('referral_code'))
                
            
        form = SignupForm(request.POST)
        if form.is_valid():

            user_email = form.cleaned_data.get('email')
            full_name = form.cleaned_data.get('full_name')
            if form.cleaned_data.get('password'):
                user_phone_no = form.cleaned_data.get('password')

            user_password = form.cleaned_data.get('password')


            otp = SignUpUserOTP.generate_otp()
            print("created otp is ", otp)
            SignUpUserOTP.objects.update_or_create(email=user_email, defaults={"otp": otp})
            
            # otp sending session
            html_content = render_to_string("emails/otp_signup.html", {"full_name": full_name, "otp": otp})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is {otp} ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user_email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()
            

            # destroying previous session
            request.session.pop("otp_verified", None)

            request.session['user_email'] = user_email
            request.session['user_full_name'] = full_name
            request.session['user_phone_no'] = user_phone_no
            request.session['user_password'] = user_password


            success_notify(request, "We sent you an OTP. Please verify your email.")
            
            return redirect("verify_signup_otp")

        
        return render(request, 'accounts/signup1.html', {"form": form})
    
@method_decorator(never_cache, name='dispatch')
class VerifySignUpOTPView(View):
    def get(self, request):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)

        if request.session.get("otp_verified"):

            return redirect("signin")
        if not request.session.get('user_email'):
            return redirect('signup')
        
        full_name = request.session.get('user_full_name')
        user_email = request.session.get('user_email')
        user_phone_no = request.session.get('user_phone_no')
        user_password = request.session.get('user_password')
        
        


        
        
        
        context = {
            "full_name": full_name,
              "user_email": user_email,
              "user_phone_no": user_phone_no,
              "user_password": user_password
              }
        return render(request, "accounts/verify_signup_otp.html", context)
    
    def post(self, request):
        entered_otp = request.POST.get("otp")
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone_no = request.POST.get("phone_no")
        password = request.POST.get("password")

        if not (full_name and email and phone_no and password ):
            return redirect('signup')
        
        otp_obj = get_object_or_404(SignUpUserOTP, email=email)


        if not entered_otp:
            error_notify(request, "enter your otp")
            return redirect('verify_signup_otp')

        if otp_obj.otp == entered_otp and otp_obj.created_at >=  timezone.now() - timedelta(minutes=5):

            # make session and clear previos session
            request.session["otp_verified"] = True

            user = CustomUser.objects.create_user(
                email=email,
                full_name=full_name,
                password=password,
                phone_no=phone_no
            )
            user.set_password(password)
            user.is_active=True
            user.save()

            otp_obj.delete()
            if request.session.get('referral_code'):
                ref_code = request.session.get('referral_code')
                try:
                    referral = Referral.objects.get(code=ref_code)
                    user.referral.referred_by = referral.user
                    user.referral.save()
                    referral_credit = referral_amount()
                    wallet = get_object_or_404(Wallet, user=referral.user)
                    transaction = wallet.credit(Decimal(referral_credit), message=f"Referral bonus from {user.full_name}" )
                    del request.session['referral_code']
                except Referral.DoesNotExist:
                    pass
            
            del request.session['user_email']
            del request.session['user_full_name']
            del request.session['user_phone_no']
            del request.session['user_password']

            success_notify(request, "Your account has been verified. You can log in now.")
            return redirect("signin")
        else:
            otp_obj.delete()
            error_notify('otp expiried try again')
            return redirect("signup")
        
@method_decorator(never_cache, name='dispatch')
class ResendSignUpOTPView(View):
    def get(self, request):
        user_email = request.session.get('user_email')
        full_name = request.session.get('user_full_name')
        otp = SignUpUserOTP.generate_otp()
        print("resend otp is ", otp)
        SignUpUserOTP.objects.update_or_create(email=user_email, defaults={"otp": otp})
        
        
        html_content = render_to_string("emails/otp_signup.html", {"full_name": full_name, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Resend OTP - Verify Your Account",
            body=f"Your new OTP is {otp}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        
        
        success_notify(request, "A new OTP has been sent to your email.")
        return redirect('verify_signup_otp')
        

# Sign in side
    
@method_decorator(never_cache, name='dispatch')
class SigninView(View):

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
        
        # this is important because chaange password safety
        if request.session.get("forgot_otp_verified"):
            request.session.pop("forgot_otp_verified", None)

        # if request.session.get("otp_verified"):
        #     return redirect("sig")
        errors = request.session.pop("signin_errors", None)
        data = request.session.pop("signin_data", None)

        form = SigninForm(data if data else None)

        if errors:
            form._errors = errors
        return render(request, 'accounts/signin1.html', {"form": form})
    
    def post(self, request):
        form = SigninForm(request.POST)

        if form.is_valid():
            emails = request.POST.get("email")
            passwords = request.POST.get("password")

            # Check if email exists

            if CustomUser.objects.filter(email=emails).exists():

                user_obj = get_object_or_404(CustomUser, email=emails)
                print("the customer active status:", user_obj.is_active)
                if not user_obj.is_active:
                    request.session["signin_errors"] = {"email": ["This email is blocked"]}
                    request.session["signin_data"] = request.POST
                    return redirect("signin")
                
                # Authenticate user
            user = authenticate(request, email=emails, password=passwords)

            if user is None:
                request.session["signin_errors"] = {
                    "email": ["Invalid credentials"],
                    "password": ["Invalid credentials"]
                    }
                request.session["signin_data"] = request.POST
                return redirect("signin")
            print('enter email:', emails )
            print('enter email:', passwords )
            user.status = True
            if user.is_superuser:
                request.session.pop("otp_verified", None)

                login(request, user)
                success_notify(request, "Login successful! You're now on the Notevia admin dashboard page.")
                return redirect('admin-dash', user_id= user.id)
            else:
                request.session.pop("otp_verified", None)
                login(request, user)
                success_notify(request, "Login successful! You're now on the Notevia home page.")
                return redirect("cores-home", user_id=user.id)
        else:
            request.session["signin_errors"] = form.errors
            request.session["signin_data"] = request.POST
            return redirect("signin")
    

# Sign out side 
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
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
    



# Forgot pass word part 
@method_decorator(never_cache, name='dispatch')
@method_decorator(cache_control(no_cache=True, no_store=True, must_revalidate=True), name='dispatch')
class ForgotPassView(View):

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        if request.session.get("forgot_otp_verified"):
            request.session.pop("forgot_otp_verified", None)

        
        if request.session.get("forgot_otp_request"):
            request.session.pop("forgot_otp_request", None)
            
        # if request.session.get("forgot_otp_verified"):

        #     return render(request, '')
            
        return render(request, 'accounts/forgotpass.html')
    
    def post(self, request):

        email = request.POST.get('email')
        if not email:
            warning_notify(request, 'enter proper email')
            return redirect('forgot_pass')


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
        request.session["forgot_otp_request"] = True
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

            warning_notify(request, "Change password then move forward")
            return redirect('new_pass', user_id=user_id)
        
        if not request.session.get("forgot_otp_request"):
            error_notify(request, 'try again something went wrong')
            return redirect('forgot_pass')
        
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
            if request.session.get("forgot_otp_request"):
                request.session.pop("forgot_otp_request", None)

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

        if not request.session.get("forgot_otp_verified"):

            error_notify(request, "You can't able to change password try again")
            return redirect("forgot_pass")



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
    
    # end of the account configration parrt
    

# """start the user profile side """
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CustomerProfileView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)


        user_profile, created = UserProfile.objects.get_or_create(user=user)

        if created:
            print("✅ A new profile was created for this user.")
            
        return render(request, 'customer/customer_profile.html', {"user_id": request.user.id, "user": user, "user_profile": user_profile})
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ChangeProfileView(View):

    def post(self, request):

        profile = request.FILES.get('profile')

        print("profile", profile)

        user = request.user

        user_profile = get_object_or_404(UserProfile, user=user)

        MAX_FILE_SIZE_MB = 2
        if profile:

            if user_profile.image and user_profile.image.public_id:
                try:
                    destroy(user_profile.image.public_id)
                    print(f"Deleted old image: {user_profile.image.public_id}")
                except Exception as e:
                    print(f"Error deleting old image: {e}")

            file_size = profile.size / (1024 * 1024)  # Convert bytes → MB

            print("profile size", profile.size)

            upload_size = profile.size / (1024 * 1024)
            

            print("real uploaded size", upload_size)

            print("file size", file_size)
            if file_size > MAX_FILE_SIZE_MB:
                error_notify(request, f"Image too large! Max allowed size is {MAX_FILE_SIZE_MB} MB.")
                return redirect("profile_edit")

            # Save only if file size is OK
            user_profile.image = profile
            user_profile.save()

        success_notify(request, "profile updated successfully")
        return redirect("profile")
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ProfileEditView(View):

    def get(self, request):


        

        user = get_object_or_404(CustomUser, id=request.user.id)

        if request.session.get('email'):
            if UserOTP.objects.filter(user=user).exists():
                UserOTP.objects.filter(user=user).delete()
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            return redirect("profile")

        user_profile = get_object_or_404(UserProfile, user=user)

        # breadcrumb
        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "Edit Profile", "url": ""},
        ]

        contex = {
            "user_id": request.user.id,
            "user": user,
            "user_profile": user_profile,
            "breadcrumb": breadcrumb
        }

        return render(request, 'customer/profile_edit.html', contex)
    
    def post(self, request):

        full_name = request.POST.get('full_name')
        phone_no = request.POST.get('phone_no')
        
        enter_email = request.POST.get('email')

        print("full name", full_name, "phone", phone_no, "email", enter_email)

        if full_name=='':
            error_notify(request, "leave your name")
            return redirect('profile_edit')
        if phone_no=='':
            error_notify(request, "leave your contact number")
            return redirect('profile_edit')
        if enter_email=='':
            error_notify(request, "leave your contact number")
            return redirect('profile_edit')
        
        

        user = request.user
        print("user email", user.email)

        if enter_email==user.email:

            user.full_name = full_name
            user.phone_no = phone_no
            user.save()

            success_notify(request, "Successfully updated your profile details")
            return redirect("profile")

        if CustomUser.objects.filter(email=enter_email).exclude(id=user.id).exists():
            error_notify(request, "email already exists")
            return redirect('profile_edit')
        

        # user.full_name = full_name
        # user.phone_no = phone_no
        # user.save()

        # if profile:
        #     user_profile.image = profile
        #     user_profile.save()


        # user.full_name = full_name
        # user.phone_no = phone_no
        # user.save()

        

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

        request.session['full_name'] = full_name
        request.session['phone_no'] = phone_no
        request.session['email'] = enter_email
        


        success_notify(request, "We sent you an OTP. Please verify your email.")
        return redirect("verify_profile")
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class VerifyProfileOTPView(View):
    def get(self, request):
        
        if not request.user.is_authenticated:
            return redirect("sigin")
        
        if not request.session.get('email'):
            return redirect("profile")
        
        
        user = get_object_or_404(CustomUser, id=request.user.id)
        
        
        return render(request, "accounts/verify_otp.html", {"user_id": request.user.id, "user": user})
    
    def post(self, request):

        entered_otp = request.POST.get("otp")
        full_name = request.session.get('full_name')
        phone_no = request.session.get('phone_no')
        email = request.session.get('email')
        
        if not all([full_name, email, phone_no]):
            error_notify(request, "Session expired. Please try again.")

            return redirect('edit_profile')


        print("full name", full_name, "phone", phone_no, "email", email)

        user = get_object_or_404(CustomUser, id=request.user.id)
        
        otp_obj = get_object_or_404(UserOTP, user=user)


        if not entered_otp:
            error_notify(request, "check your email and enter your otp")
            return redirect('verify_profile')



        if otp_obj.otp == entered_otp and otp_obj.created_at >=  timezone.now() - timedelta(minutes=5):
            print('user is active:', user.is_active)
            
            

            # make session and clear previos session
            
            request.session["chabge_otp_verified"] = True

            user.full_name = full_name
            user.phone_no = phone_no
            user.email = email
            user.save()

            otp_obj.delete()
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            success_notify(request, "Successfully updated your profile details.")
            return redirect("profile")
        else:
            otp_obj.delete()
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            warning_notify(request, "your otp validity is over enter your mail again")
            return redirect("profile_edit")

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ResendProfileOTPView(View):
    def get(self, request):
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=request.user.id)
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
        return redirect("verify_profile")
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddressView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)

        user_profile = get_object_or_404(UserProfile, user=user)

        addresses = Address.objects.filter(user=user)
        print('addresses', addresses)

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "Address", "url": ""},
        ]

        contex = {
            "user_id": request.user.id,
            "user": user,
            "user_profile": user_profile,
            "addresses": addresses,
            "breadcrumb": breadcrumb
        }

        return render(request, 'customer/address.html', contex)
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddAddressView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)

        user_profile = get_object_or_404(UserProfile, user=user)

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "Address", "url": "/accounts/user_address/"},
            {"name": "Add Address", "url": "/accounts/user_address/"}
        ]

        contex = {
            "user_id": request.user.id,
            "user": user,
            "user_profile": user_profile,
            "breadcrumb": breadcrumb
        }


        return render(request, 'customer/add_address.html', contex)
    
    def post(self, request):

        full_name = request.POST.get('full_name').strip()
        email = request.POST.get('email').strip()
        address = request.POST.get('address').strip()
        district = request.POST.get('district').strip()
        state = request.POST.get('state').strip()
        city = request.POST.get('city').strip()
        pincode = request.POST.get('pincode').strip()
        phone_no = request.POST.get('phone_no').strip()
        address_type = request.POST.get('addressType')

        if not full_name:

            error_notify(request, "leave your name")
            return redirect('add_address')
        elif not re.match(r'^[A-Za-z\s]+$', full_name):
            error_notify(request, "Name can contain only alphabets and spaces.")
            return redirect('add_address')
        

        if not email:

            error_notify(request, "leave your email")
            return redirect('add_address')
        if not address:

            error_notify(request, "leave your proper address")
            return redirect('add_address')
        if not district:

            error_notify(request, "leave your proper district")
            return redirect('add_address')
        
        if not state:

            error_notify(request, "leave your proper state")
            return redirect('add_address')
        if not state:

            error_notify(request, "leave your proper state")
            return redirect('add_address')
        if not city:

            error_notify(request, "leave your proper city")
            return redirect('add_address')
        if not pincode:

            error_notify(request, "leave your proper pincode")
            return redirect('add_address')
        if not phone_no:

            error_notify(request, "leave your proper contact number")
            return redirect('add_address')
        if len(phone_no) != 10  :

            error_notify(request, "contact number must be exactly 10 digits")
            return redirect('add_address')

        user = get_object_or_404(CustomUser, id=request.user.id)


        print('address type', address_type, "name", full_name,"address", address)

        address = Address.objects.create(user=user, full_name=full_name, email=email, address=address, 
                                         district=district, state=state, city=city, pin_code=pincode, phone_no=phone_no, address_type=address_type)
        success_notify(request, "new address created successfully ")
        return redirect('address')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditAddressView(View):
    def get(self, request, address_id):

        user = get_object_or_404(CustomUser, id=request.user.id)

        user_profile = get_object_or_404(UserProfile, user=user)

        edit_address = get_object_or_404(Address, id=address_id)

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "Address", "url": "/accounts/user_address/"},
            {"name": "Edit Address", "url": "/accounts/user_address/"}
        ]

        contex = {
            "user_id": request.user.id, 
            "user": user, 
            "user_profile": user_profile, 
            "edit_address": edit_address,
            "breadcrumb": breadcrumb
            
        }
        return render(request, 'customer/add_address.html', contex)
    def post(self, request, address_id):

        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email').strip()
        address = request.POST.get('address').strip()
        district = request.POST.get('district').strip()
        state = request.POST.get('state').strip()
        city = request.POST.get('city').strip()
        pincode = request.POST.get('pincode').strip()
        phone_no = request.POST.get('phone_no').strip()
        address_type = request.POST.get('addressType')

        print('address type', address_type, "name", full_name,"address", address)

        if not full_name or len(full_name) < 3:

            error_notify(request, "leave your name")
            return redirect('edit_address', address_id=address_id)
        elif not re.match(r'^[A-Za-z\s]+$', full_name):
            error_notify(request, "Name can contain only alphabets and spaces.")
            return redirect('edit_address', address_id=address_id)
        

        if not email:

            error_notify(request, "leave your email")
            return redirect('edit_address', address_id=address_id)
        if not address:

            error_notify(request, "leave your proper address")
            return redirect('edit_address', address_id=address_id)
        if not district:

            error_notify(request, "leave your proper district")
            return redirect('edit_address', address_id=address_id)
        
        if not state:

            error_notify(request, "leave your proper state")
            return redirect('edit_address', address_id=address_id)
        if not state:

            error_notify(request, "leave your proper state")
            return redirect('edit_address', address_id=address_id)
        if not city:

            error_notify(request, "leave your proper city")
            return redirect('edit_address', address_id=address_id)
        if not pincode:

            error_notify(request, "leave your proper pincode")
            return redirect('edit_address', address_id=address_id)
        if not phone_no:

            error_notify(request, "leave your proper contact number")
            return redirect('edit_address', address_id=address_id)
        if len(phone_no) != 10  :

            error_notify(request, "contact number must be exactly 10 digits")
            return redirect('edit_address', address_id=address_id)
        
        edit_address = get_object_or_404(Address, id=address_id)
        edit_address.full_name = full_name
        edit_address.email = email
        edit_address.address = address
        edit_address.district = district
        edit_address.state = state
        edit_address.city = city
        edit_address.pin_code = pincode
        edit_address.address_type = address_type
        edit_address.phone_no = phone_no
        edit_address.save()

        success_notify(request, "address updated successfully ")
        return redirect('address')

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class SetDefaultView(View):

    def get(self, request, address_id):
        set_main = request.GET.get('set_main')
        print('set_main: ', set_main, address_id)

        addresses = Address.objects.all().exclude(id=address_id)

        if addresses:
            print('inside if')

            for address in addresses:
                address.is_default = False
                print(f"address",address.full_name,"-", address.is_default)
                address.save()

        print("all address:", addresses)

        main_address = get_object_or_404(Address, id=address_id)
        main_address.is_default = set_main
        main_address.save()
        print("main_addresss set default:", main_address.is_default)
        

        return redirect('address')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class RemoveAddressView(View):

    def get(self, request, address_id):

        is_delete = request.GET.get('delete')

        if is_delete:
            print('delete address', address_id, is_delete)
            delete_address = get_object_or_404(Address, id=address_id).delete()
            

        return redirect('address')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ChangePassWordView(View):

    def get(self, request):

        context = {
            "user_id": request.user.id,
            "user_profile": profile(request)
        }
        return render(request, 'customer/change_user_pass.html', context)