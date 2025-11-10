from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser, UserOTP, UserProfile, Address
from .forms import SignupForm
from django.utils import timezone
from datetime import timedelta
from  django.contrib.auth import authenticate, login, logout
from .utils import success_notify, error_notify, warning_notify, info_notify, referral_amount
from django.views.decorators.cache import never_cache, cache_control
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from cloudinary.uploader import destroy
import re
from products.models import Referral, Wishlist
from cart.models import Wallet
from decimal import Decimal



# Create your views here.
@method_decorator(never_cache, name='dispatch')
class SignupView(View):
    
    def get(self, request):
        
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        if request.session.get('signup_user'):
            signup_user_id = request.session.get('signup_user')
            if CustomUser.objects.filter(id=signup_user_id).exists():

                signup_user = get_object_or_404(CustomUser, id=signup_user_id)
                wallet = Wallet.objects.filter(user=signup_user).delete()
                referral = Referral.objects.filter(user=signup_user).delete()
                wishlist = Wishlist.objects.create(user=signup_user).delete()
                if UserOTP.objects.filter(user=signup_user).exists():
                    UserOTP.objects.filter(user=signup_user).delete()
                signup_user.delete()
            del request.session['signup_user']
            

        # if request.session.get("signup_done"):
        #     return redirect("verify-otp", user_id=request.user.id)

        # this is important because chaange password safety
        if request.session.get("forgot_otp_verified"):
            request.session.pop("forgot_otp_verified", None)
        
        form = SignupForm()
        return render(request, 'accounts/signup.html', {"form": form})
    
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
        
        request.session['signup_user'] = user.id
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
            if request.session.get('referral_code'):
                ref_code = request.session.get('referral_code')
                try:
                    referral = Referral.objects.get(code=ref_code)
                    user.referral.referred_by = referral.user
                    user.referral.save()
                    referral_credit = referral_amount()
                    wallet = get_object_or_404(Wallet, user=referral.user)
                    transaction = wallet.credit(Decimal(referral_credit), message=f"Referral bonus from {user.full_name}" )

                except Referral.DoesNotExist:
                    pass
            del request.session['referral_code']
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
        
        return render(request, 'accounts/signin1.html')
    
    def post(self, request):

        emails = request.POST.get("email")
        passwords = request.POST.get("password")
        # users = CustomUser.objects.get(email=emails)

        if not emails:
            
            warning_notify(request, "enter the mail")
            return redirect('signin')
        if not passwords:
            
            warning_notify(request, "enter your password")
            return redirect('signin')
        
        if CustomUser.objects.filter(email=emails).exists():

            user = get_object_or_404(CustomUser, email=emails)
            print("the customer active status:", user.is_active)
            if not user.is_active:
                error_notify(request, "this mail is blocked, use different mail")
                return redirect("signin")
    
        # user1 = CustomUser.objects.get(email=emails)
        user = authenticate(request, email=emails, password=passwords)

        # print("user status active: ", user.is_active)
        
        print("email is", emails)
        print("password is ", passwords)
        print(" usser is authenticated :",user)
        if user is not None:
            user.status = True
            print("user status", user.status)
            if user.is_superuser:
                request.session.pop("otp_verified", None)

                login(request, user)

                return redirect('admin-dash', user_id= user.id)
            else:
                request.session.pop("otp_verified", None)
                login(request, user)

                return redirect("cores-home", user_id=user.id)
        error_notify(request, "invalid credentials")
        return redirect('signin')
    

# Sign out side 

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


# Forgot pass word part 

class ForgotPassView(View):

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin-dash', user_id= request.user.id)
            else:
                return redirect("cores-home", user_id=request.user.id)
            
        if request.session.get("forgot_otp_verified"):
            request.session.pop("forgot_otp_verified", None)
            
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

            warning_notify(request, "Change password then move forward")
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

class CustomerProfileView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)


        user_profile, created = UserProfile.objects.get_or_create(user=user)

        if created:
            print("✅ A new profile was created for this user.")
            
        return render(request, 'customer/customer_profile.html', {"user_id": request.user.id, "user": user, "user_profile": user_profile})
    
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
    

@method_decorator(never_cache, name='dispatch')
class VerifyProfileOTPView(View):
    def get(self, request):
        
        if not request.user.is_authenticated:
            return redirect("sigin")
        
        if not request.session.get('email'):
            return redirect("profile")
            
        # if not request.session.get("signup_done"):

        #     return redirect("signup") 

        # forgot otp session check
        
        # if request.session.get("forgot_otp_verified"):

        #     warning_notify(request, "Change password then move forward")
        #     return redirect('new_pass', user_id=user_id)
        
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
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
    
class RemoveAddressView(View):

    def get(self, request, address_id):

        is_delete = request.GET.get('delete')

        if is_delete:
            print('delete address', address_id, is_delete)
            delete_address = get_object_or_404(Address, id=address_id).delete()
            

        return redirect('address')
    
