from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser, UserOTP, UserProfile, Address, SignUpUserOTP
from .forms import SignupForm, SigninForm, AddressForm, ChangePasswordForm
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
from cart.models import Wallet, WalletTransaction
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from orders.models import Order, OrderItem, OrderAddress
from time import time
from offers.models import Coupon, CouponUsage

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
            try:
                session_email = request.session.get('user_email')
                SignUpUserOTP.objects.filter(email=session_email).delete()
            except:
                del request.session['user_email']
                del request.session['user_full_name']
                del request.session['user_phone_no']
                del request.session['user_password']
            del request.session['user_email']
            del request.session['user_full_name']
            del request.session['user_phone_no']
            del request.session['user_password']
            
            return redirect('signup')
        if request.session.get('signup_otpExpiry'):
            del request.session['signup_otpExpiry']
        
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
                
                
            
        form = SignupForm(request.POST)
        if form.is_valid():

            user_email = form.cleaned_data.get('email')
            full_name = form.cleaned_data.get('full_name')
            if form.cleaned_data.get('password'):
                user_phone_no = form.cleaned_data.get('phone_no')

            user_password = form.cleaned_data.get('password')


            otp = SignUpUserOTP.generate_otp()
            
            SignUpUserOTP.objects.update_or_create(email=user_email, defaults={"otp": otp})
            
            # otp sending session
            html_content = render_to_string("emails/otp_signup.html", {"full_name": full_name, "otp": otp})
            email = EmailMultiAlternatives(
                subject="Signup Verify Your Account",
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
            expiry_time = int(time()) + 180  # 180 seconds
            request.session["signup_otpExpiry"] = expiry_time
            request.session.modified = True

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
        if not request.session.get('signup_otpExpiry'):
            return redirect('signup')
        

        
        full_name = request.session.get('user_full_name')
        user_email = request.session.get('user_email')
        user_phone_no = request.session.get('user_phone_no')
        user_password = request.session.get('user_password')
        expiry_time = request.session.get("signup_otpExpiry", 0)
        


        
        
        
        context = {
            "full_name": full_name,
              "user_email": user_email,
              "user_phone_no": user_phone_no,
              "user_password": user_password,
              "expiry": expiry_time,
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

        if otp_obj.otp == entered_otp and otp_obj.updated_at >=  timezone.now() - timedelta(minutes=3):

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
                    transaction = wallet.credit(Decimal(referral_credit), message=f"Congrats {referral.user.full_name}! Your friend {full_name} used your referral code and the bonus is now added" )
                    del request.session['referral_code']
                except Referral.DoesNotExist:
                    info_notify(request, "Some thing went wrong in referral process")
            
            del request.session['user_email']
            del request.session['user_full_name']
            del request.session['user_phone_no']
            del request.session['user_password']
            del request.session['signup_otpExpiry']

            success_notify(request, "Your account has been verified. You can log in now.")
            return redirect("signin")
        else:
            otp_obj.delete()
            error_notify('otp expiried try again')
            return redirect("signup")
        
@method_decorator(never_cache, name='dispatch')
class ResendSignUpOTPView(View):
    def post(self, request):
        if not request.session.get('signup_otpExpiry'):
            return redirect('signup')
        if not request.session.get('user_email'):
            return redirect('signup')
        user_email = request.session.get('user_email')
        full_name = request.session.get('user_full_name')
        otp = SignUpUserOTP.generate_otp()
        
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

        
        request.session["signup_otpExpiry"] = int(time()) + 180
        
        
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

        if 'next' in request.GET:
            info_notify(request, "User is not logged in, please log in to continue.")
        return render(request, 'accounts/signin1.html', {"form": form})
    
    def post(self, request):
        form = SigninForm(request.POST)

        if form.is_valid():
            emails = request.POST.get("email")
            passwords = request.POST.get("password")

            # Check if email exists

            if CustomUser.objects.filter(email=emails).exists():

                user_obj = get_object_or_404(CustomUser, email=emails)
                
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

        wallet_confirm = request.session.get('wallet_payment_confirm')
        transaction_id = request.session.get('session_transaction')

        # If required session keys are missing → clear & redirect
        if  wallet_confirm and transaction_id:
            

            # Get wallet
            if not Wallet.objects.filter(user=request.user).exists():
                request.session.pop('wallet_payment_confirm', None)
                request.session.pop('session_transaction', None)
                return redirect('wallet')

            session_wallet = get_object_or_404(Wallet, user=request.user)

            # Validate transaction
            if not WalletTransaction.objects.filter(wallet=session_wallet, id=transaction_id).exists():
                request.session.pop('wallet_payment_confirm', None)
                request.session.pop('session_transaction', None)
                return redirect('wallet')

            session_transaction = get_object_or_404(WalletTransaction, id=transaction_id)

            # Process wallet logic
            session_wallet.set_wallet_amount(session_transaction.amount)
            session_transaction.delete()

            # Clean up session keys
            request.session.pop('wallet_payment_confirm', None)
            request.session.pop('session_transaction', None)

            #error_notify(request, 'Try again, payment gateway failed..!')
            
        else:
            request.session.pop('wallet_payment_confirm', None)
            request.session.pop('session_transaction', None)

        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'Try again, payment gateway failed..!')

        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        if request.session.get('selected_address'):
                request.session.pop('selected_address', None)
        logout(request)
        user.status = False
        
        

        return redirect('signin')
    def post(self, request, user_id):

        wallet_confirm = request.session.get('wallet_payment_confirm')
        transaction_id = request.session.get('session_transaction')

        # If required session keys are missing → clear & redirect
        if  wallet_confirm and transaction_id:
            

            # Get wallet
            if not Wallet.objects.filter(user=request.user).exists():
                request.session.pop('wallet_payment_confirm', None)
                request.session.pop('session_transaction', None)
                return redirect('wallet')

            session_wallet = get_object_or_404(Wallet, user=request.user)

            # Validate transaction
            if not WalletTransaction.objects.filter(wallet=session_wallet, id=transaction_id).exists():
                request.session.pop('wallet_payment_confirm', None)
                request.session.pop('session_transaction', None)
                return redirect('wallet')

            session_transaction = get_object_or_404(WalletTransaction, id=transaction_id)

            # Process wallet logic
            session_wallet.set_wallet_amount(session_transaction.amount)
            session_transaction.delete()

            # Clean up session keys
            request.session.pop('wallet_payment_confirm', None)
            request.session.pop('session_transaction', None)

            error_notify(request, 'Try again, payment gateway failed..!')
            
        else:
            request.session.pop('wallet_payment_confirm', None)
            request.session.pop('session_transaction', None)
        
        if request.session.get('payment_confirm'):
            if request.session.get('session_order'):
                order_id = request.session.get('session_order')
                try:
                    session_order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    request.session.pop('payment_confirm', None)
                    del request.session['session_order']
                    return redirect('cart_page')
                # session_order = get_object_or_404(Order, id=order_id)
                if session_order.coupon_code:
                    used_coupon = get_object_or_404(Coupon, code=session_order.coupon_code)
                    update_usage = used_coupon.decrement_usage(request.user)
                for item in session_order.items.all():
                    item.variant.stock += item.quantity
                    item.variant.save()
                    
                session_order.items.all().delete()
                session_order.orders_address.delete()
                session_order.delete()
            request.session.pop('payment_confirm', None)
            del request.session['session_order']
            
            error_notify(request, 'Try again, payment gateway failed..!')
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        if request.session.get('selected_address'):
                request.session.pop('selected_address', None)
        logout(request)
        user.status = False
        

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
            
            if request.session.get("otpExpiry"):
                
                del request.session["otpExpiry"]
            if request.session.get("forgot_email"):
                try:
                    forgot_email = request.session.get("forgot_email")
                    user = get_object_or_404(CustomUser, email=forgot_email)
                except:
                    request.session.pop("forgot_otp_request", None)
                    request.session.pop("forgot_email", None)
            UserOTP.objects.filter(user=user).delete()
            request.session.pop("forgot_otp_request", None)
            request.session.pop("forgot_email", None)
            
        
            
        return render(request, 'accounts/forgotpass.html')
    
    def post(self, request):

        enter_email = request.POST.get('email')
        if not enter_email:
            warning_notify(request, 'enter proper email')
            return redirect('forgot_pass')


        if not CustomUser.objects.filter(email=enter_email).exists():
            error_notify(request, 'thre is no account use this email')
            return redirect('forgot_pass')
        
        user = get_object_or_404(CustomUser, email=enter_email)
        
        otp = UserOTP.generate_otp()
        
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
        expiry_time = int(time()) + 180  # 180 seconds
        request.session["otpExpiry"] = expiry_time
        request.session.modified = True
        request.session["forgot_otp_request"] = True
        request.session["forgot_email"] = enter_email
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
            if not request.session.get("otpExpiry"):

                error_notify(request, 'try again something went wrong')
                return redirect('forgot_pass')
        
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        expiry_time = request.session.get("otpExpiry", 0)

        context = {
            "user_id": user_id,
            "user": user,
            "expiry": expiry_time,
        }
        
        return render(request, "accounts/verify_forgot_otp.html", context)
    
    def post(self, request, user_id):
        entered_otp = request.POST.get("otp")
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=user_id)
        # otp_obj = UserOTP.objects.get(user=user)# add get_object_or_404
        otp_obj = get_object_or_404(UserOTP, user=user)


        if not entered_otp:
            error_notify(request, "check your email and enter your otp")
            return redirect('verify_forgot_otp', user_id=user.id)

        if otp_obj.otp == entered_otp and otp_obj.updated_at >=  timezone.now() - timedelta(minutes=3):
            
            
            

            # make session and clear previos session
            # request.session.pop("signup_done", None)
            request.session["forgot_otp_verified"] = True
            if request.session.get("forgot_otp_request"):
                
                del request.session["otpExpiry"]
                request.session.pop("forgot_otp_request", None)
                request.session.pop("forgot_email", None)

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
        if not request.session.get("otpExpiry"):
            return redirect("forgot_pass")
        user = get_object_or_404(CustomUser, id=user_id)
        otp = UserOTP.generate_otp()
        
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

        new_expiry = int(time()) + 180
        request.session["otpExpiry"] = new_expiry
        
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


        # user_profile, created = UserProfile.objects.get_or_create(user=user)

        
        user_profile = profile(request)
        
            
        return render(request, 'customer/customer_profile.html', {"user_id": request.user.id, "user": user, "user_profile": user_profile})
    

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ChangeProfileView(View):

    def post(self, request):

        profile = request.FILES.get('profile')

        

        user = request.user

        user_profile = get_object_or_404(UserProfile, user=user)

        MAX_FILE_SIZE_MB = 2
        if profile:

            if user_profile.image and user_profile.image.public_id:
                try:
                    destroy(user_profile.image.public_id)
                    
                except Exception as e:
                    error_notify(request, f"Error deleting old image: {e}")

            file_size = profile.size / (1024 * 1024)  # Convert bytes → MB

            

            upload_size = profile.size / (1024 * 1024)
            

            
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

        if request.session.get('email') or request.session.get('profile_otpExpiry'):
            if SignUpUserOTP.objects.filter(email=request.session.get('email')).exists():
                SignUpUserOTP.objects.filter(email=request.session.get('email')).delete()
            if UserOTP.objects.filter(user=user).exists():
                UserOTP.objects.filter(user=user).delete()
            request.session.pop("new_mail_otp_verified", None)
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            request.session.pop("profile_otpExpiry", None)
            request.session.pop("profile_otpExpiry", None)
            return redirect("profile")

        

        # user_profile = get_object_or_404(UserProfile, user=user)
        user_profile = profile(request)

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

        

        if full_name=='':
            error_notify(request, "leave your name")
            return redirect('profile_edit')
        if phone_no=='':
            error_notify(request, "leave your contact number")
            return redirect('profile_edit')
        if enter_email=='':
            error_notify(request, "leave your email")
            return redirect('profile_edit')
        
        

        user = request.user
        
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

        

        otp = SignUpUserOTP.generate_otp()
        
        SignUpUserOTP.objects.update_or_create(email=enter_email, defaults={"otp": otp})
        
        # otp sending session
        html_content = render_to_string("emails/otp_profile.html", {"full_name": full_name, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Verify Your New Email",
            body=f"Your OTP is {otp} ",
            from_email=settings.EMAIL_HOST_USER,
            to=[enter_email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send()

        request.session['full_name'] = full_name
        request.session['phone_no'] = phone_no
        request.session['email'] = enter_email
        request.session["profile_otpExpiry"] = int(time()) + 180
        request.session.modified = True
        


        success_notify(request, "We sent you an OTP. Please verify your email.")
        return redirect("verify_new_mail")
    
class VerifyNewMailView(View):
    def get(self, request):

        if not request.user.is_authenticated:
            return redirect("sigin")
        if not request.session.get('email'):
            # info_notify(request, "try again")
            return redirect("profile")
        
        if not request.session.get('profile_otpExpiry'):
            info_notify(request, "try again something went wrong.")
            return redirect('profile')
        
        
        if request.session.get("new_mail_otp_verified"):
            if not request.session.get('profile_mail_otpExpiry'):
                info_notify(request, "something went wrong try agian")
                UserOTP.objects.filter(user=request.user).delete()
                del request.session['profile_mail_otpExpiry']
                request.session.pop("new_mail_otp_verified", None)
                return redirect('profile_edit')
            info_notify(request, "verify your old mail, then only the mail can update")
            return redirect('verify_profile')
        
        
        expiry_time = request.session.get('profile_otpExpiry')

        context = {
            "email" : request.session.get('email'),
            'expiry': expiry_time,
        }
        return render(request, "accounts/verify_otp.html", context)
    
    def post(self, request):

        full_name = request.session.get('full_name')
        phone_no = request.session.get('phone_no')
        new_email = request.session.get('email')
        if not all([full_name, new_email, phone_no]):
            error_notify(request, "Session expired. Please try again.")

            return redirect('profile_edit')
        
        if not request.session.get('email'):
            
            return redirect('verify_new_mail')

        if not request.POST.get("otp"):
            error_notify(request, "check your email and enter your otp")
            return redirect('verify_new_mail')
        entered_otp = request.POST.get("otp")

        if not SignUpUserOTP.objects.filter(email=new_email):
            error_notify(request, "Otp is expired, try again ")
            return redirect('profile_edit')
        
        otp_obj = get_object_or_404(SignUpUserOTP, email=new_email)

        if otp_obj.updated_at >=  timezone.now() - timedelta(minutes=3):
            
            if otp_obj.otp != entered_otp:
                attempt = request.session.get('otp_attempt', 0) + 1
                request.session['otp_attempt'] = attempt
                
                if attempt > 3:
                    
                    request.session.pop('otp_attempt', None)
                    info_notify(request, 'OTP is wrong, try again')
                    return redirect('profile_edit')
                info_notify(request, f'OTP is wrong, try again. Attempts left:{4 - attempt}')
                return redirect('verify_new_mail')

            user = request.user
            
            otp = UserOTP.generate_otp()
            
            UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
            
            # otp sending session
            html_content = render_to_string("emails/otp_profile.html", {"user": user, "otp": otp})
            email = EmailMultiAlternatives(
                subject="Verify Your Account",
                body=f"Your OTP is {otp} ",
                from_email=settings.EMAIL_HOST_USER,
                to=[user.email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

            request.session["new_mail_otp_verified"] = True
            request.session.pop('otp_attempt', None)
            del request.session['profile_otpExpiry']

            otp_obj.delete()
            request.session["profile_mail_otpExpiry"] = int(time()) + 180
            success_notify(request, "new user mail is verified, We sent you an OTP to old mail. Please verify your email.")
            return redirect("verify_profile")
        else:
            otp_obj.delete()
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            del request.session['profile_otpExpiry']
            warning_notify(request, "your otp validity is over enter your mail again")
            return redirect("profile_edit")
            

class ResendNewMailOtpView(View):

    def get(self, request):

        full_name = request.session.get('full_name')
        phone_no = request.session.get('phone_no')
        new_email = request.session.get('email')
        if not all([full_name, new_email, phone_no]):
            error_notify(request, "Session expired. Please try again.")

            return redirect('profile_edit')

        # email = request.session.get('email')
        otp = SignUpUserOTP.generate_otp()
        
        new_mail_otp = SignUpUserOTP.objects.update_or_create(email=new_email, defaults={"otp": otp})
        
        # otp sending session
        html_content = render_to_string("emails/otp_profile.html", {"full_name": full_name, "otp": otp})
        email = EmailMultiAlternatives(
            subject="Verify Your Account",
            body=f"Your OTP is {otp} ",
            from_email=settings.EMAIL_HOST_USER,
            to=[new_email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send()

        request.session["profile_otpExpiry"] = int(time()) + 180
        request.session.pop('otp_attempt', None)

        success_notify(request, "A new OTP has been sent to your email.")
        return redirect("verify_new_mail")

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class VerifyProfileOTPView(View):
    def get(self, request):
        
        if not request.user.is_authenticated:
            return redirect("sigin")
        
        if not request.session.get("new_mail_otp_verified") or not request.session.get('profile_mail_otpExpiry'):
            
            return redirect('profile_edit')
        
        if not request.session.get('email'):
            info_notify(request, "try again")
            return redirect("profile")
        
        
        user = get_object_or_404(CustomUser, id=request.user.id)
        expiry_time = request.session.get('profile_mail_otpExpiry')
        context = {
            "user_id": request.user.id,
            "user": user,
            'expiry': expiry_time,
        }
        
        return render(request, "accounts/verify_otp.html", context)
    
    def post(self, request):

        entered_otp = request.POST.get("otp")
        full_name = request.session.get('full_name')
        phone_no = request.session.get('phone_no')
        email = request.session.get('email')
        
        if not all([full_name, email, phone_no]):
            error_notify(request, "Session expired. Please try again.")

            return redirect('profile_edit')


        

        user = get_object_or_404(CustomUser, id=request.user.id)
        
        otp_obj = get_object_or_404(UserOTP, user=user)


        if not entered_otp:
            error_notify(request, "check your email and enter your otp")
            return redirect('verify_profile')



        if otp_obj.updated_at >=  timezone.now() - timedelta(minutes=3):
            

            if otp_obj.otp != entered_otp:
                attempt = request.session.get('otp_attempt', 0) + 1
                request.session['otp_attempt'] = attempt
                
                if attempt > 3:
                    request.session.pop('otp_attempt', None)
                    info_notify(request, 'OTP is wrong, try again')
                    return redirect('profile_edit')
                info_notify(request, f'OTP is wrong, try again. Attempts left:{4 - attempt}')
                return redirect('verify_profile')
            

            

            user.full_name = full_name
            user.phone_no = phone_no
            user.email = email
            user.save()
            
            request.session.pop('otp_attempt', None)
            request.session.pop("new_mail_otp_verified", None)
            otp_obj.delete()
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            del request.session['profile_mail_otpExpiry']
            success_notify(request, "Successfully updated your profile details.")
            return redirect("profile")
        else:
            otp_obj.delete()
            request.session.pop("new_mail_otp_verified", None)
            del request.session['full_name']
            del request.session['email']
            del request.session['phone_no']
            del request.session['profile_mail_otpExpiry']
            warning_notify(request, "your otp validity is over enter your mail again")
            return redirect("profile_edit")

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ResendProfileOTPView(View):
    def get(self, request):
        # user = CustomUser.objects.get(id=user_id)# add get_object_or_404
        user = get_object_or_404(CustomUser, id=request.user.id)
        otp = UserOTP.generate_otp()
        
        UserOTP.objects.update_or_create(user=user, defaults={"otp": otp})
        
        
        html_content = render_to_string("emails/otp_profile.html", {"user": user, "otp": otp})
        
        email = EmailMultiAlternatives(
            subject="Resend OTP - Verify Your Account",
            body=f"Your new OTP is {otp}",
            from_email=settings.EMAIL_HOST_USER,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        request.session["profile_mail_otpExpiry"] = int(time()) + 180
        request.session.pop('otp_attempt', None)
        
        success_notify(request, "A new OTP has been sent to your email.")
        return redirect("verify_profile")
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class AddressView(View):

    def get(self, request):

        user = get_object_or_404(CustomUser, id=request.user.id)

        # user_profile = get_object_or_404(UserProfile, user=user)
        user_profile = profile(request)

        addresses = Address.objects.filter(user=user)
        

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

        user_profile = profile(request)

        errors = request.session.pop("add_address_error", None)
        data = request.session.pop("add_address_data", None)

        form = AddressForm(data if data else None)

        if errors:
            form._errors = errors

        breadcrumb = [
            {"name": "Profile", "url": "/accounts/profile/"},
            {"name": "Address", "url": "/accounts/user_address/"},
            {"name": "Add Address", "url": "/accounts/user_address/"}
        ]

        contex = {
            "user_id": request.user.id,
            "user": user,
            "user_profile": user_profile,
            "breadcrumb": breadcrumb,
            "form": form,
        }


        return render(request, 'customer/add_address.html', contex)
    
    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():

            full_name = request.POST.get('full_name').strip()
            email = request.POST.get('email').strip()
            address = request.POST.get('address_field').strip()
            district = request.POST.get('district').strip()
            state = request.POST.get('state').strip()
            city = request.POST.get('city').strip()
            pincode = request.POST.get('pincode').strip()
            phone_no = request.POST.get('phone_no').strip()
            address_type = request.POST.get('addressType')


            user = get_object_or_404(CustomUser, id=request.user.id)


            

            address = Address.objects.create(user=user, full_name=full_name, email=email, address=address, 
                                            district=district, state=state, city=city, pin_code=pincode, phone_no=phone_no, address_type=address_type)
            success_notify(request, "new address created successfully ")
            return redirect('address')
        else:
            request.session["add_address_error"] = form.errors
            request.session["add_address_data"] = request.POST
            return redirect("add_address")

    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class EditAddressView(View):
    def get(self, request, address_id):

        user = get_object_or_404(CustomUser, id=request.user.id)

        user_profile = profile(request)

        edit_address = get_object_or_404(Address, id=address_id)

        errors = request.session.pop("edit_address_error", None)
        data = request.session.pop("edit_address_data", None)

        form = AddressForm(data if data else None)

        if errors:
            form._errors = errors

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
            "breadcrumb": breadcrumb,
            "form": form
            
        }
        return render(request, 'customer/add_address.html', contex)
    def post(self, request, address_id):
        form = AddressForm(request.POST)

        if form.is_valid():
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email').strip()
            address = request.POST.get('address_field').strip()
            district = request.POST.get('district').strip()
            state = request.POST.get('state').strip()
            city = request.POST.get('city').strip()
            pincode = request.POST.get('pincode').strip()
            phone_no = request.POST.get('phone_no').strip()
            address_type = request.POST.get('addressType')

            
            
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
        else:
            request.session["edit_address_error"] = form.errors
            request.session["edit_address_data"] = request.POST
            return redirect("edit_address", address_id=address_id)

@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class SetDefaultView(View):

    def get(self, request, address_id):
        set_main = request.GET.get('set_main')
        

        addresses = Address.objects.all().exclude(id=address_id)

        if addresses:
            

            for address in addresses:
                address.is_default = False
                
                address.save()

        

        main_address = get_object_or_404(Address, id=address_id)
        main_address.is_default = set_main
        main_address.save()
        success_notify(request, f"default address is changed to {main_address.full_name}")
        
        

        return redirect('address')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class RemoveAddressView(View):

    def get(self, request, address_id):

        is_delete = request.GET.get('delete')

        if is_delete:
            
            delete_address = get_object_or_404(Address, id=address_id)
            info_notify(request, f"{delete_address.full_name} address deleted")
            delete_address.delete()

            
            

        return redirect('address')
    
@method_decorator(login_required(login_url='signin'), name='dispatch')
@method_decorator(never_cache, name='dispatch')
class ChangePassWordView(View):

    def get(self, request):

        errors = request.session.pop("change_password_error", None)
        data = request.session.pop("change_password_data", None)

        form = ChangePasswordForm(data if data else None)

        if errors:
            form._errors = errors

        context = {
            "user_id": request.user.id,
            "user_profile": profile(request),
            "form": form
        }
        return render(request, 'customer/change_user_pass.html', context)
    
    def post(self, request):


        form = ChangePasswordForm(request.POST)

        if form.is_valid():

            old_password = request.POST.get('current_password')
            New_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not request.user.check_password(old_password):
                request.session["change_password_error"] = {"current_password": ["the entered password is incorrect "]}
                request.session["change_password_data"] = request.POST
                return redirect("change_user_pass")
            
            user = request.user
            user.set_password(New_password)
            user.save()

            success_notify(request, "the password changed successfully")
            return redirect('profile')
        else:
            request.session["change_password_error"] = form.errors
            request.session["change_password_data"] = request.POST
            return redirect("change_user_pass")