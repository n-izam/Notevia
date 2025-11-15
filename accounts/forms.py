from django import forms
# from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re
from .utils import validationerror

User = get_user_model()

class SignupForm(forms.ModelForm):
    password = forms.CharField(
        
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter password"}),
    )
    confirm_password = forms.CharField(
        
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"}),
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "phone_no", "password"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name" }),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email" }),
            "phone_no": forms.TextInput(attrs={"class": "form-control", "placeholder": "10-digit Phone No (optional)"}),
        }

    # custom validations
    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        print("signup email:",full_name)
        if not re.match(r'^[A-Za-z\s]+$', full_name):
            validationerror("Name can contain only alphabets and spaces.")
        else:
            return full_name

    def clean_email(self):
        email = self.cleaned_data.get("email")
        print("signup email:",email)
        if User.objects.filter(email=email).exists():
            validationerror("Email already exists")
        else:
            return email

    def clean_phone_no(self):
        phone = self.cleaned_data.get("phone_no")
        if phone and (not phone.isdigit() or len(phone) != 10):
            validationerror("Phone number must be exactly 10 digits")
        else:
            return phone

    def clean_password(self):
        password = self.cleaned_data.get("password")
        print("signup pass:",password)
        # at least 8 chars, upper, lower, number, special char
        if len(password) < 8:
            validationerror("Password must be at least 8 characters long")
        elif not re.search(r"[A-Z]", password):
            validationerror("Password must contain at least one uppercase letter")
        elif not re.search(r"[a-z]", password):
            raise validationerror("Password must contain at least one lowercase letter")
        elif not re.search(r"[0-9]", password):
            raise validationerror("Password must contain at least one digit")
        elif not re.search(r"[@$!%*?&]", password):
            raise validationerror("Password must contain at least one special character (@, $, !, %, *, ?, &)")
        else:
            return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match")
            
class SigninForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)


class AddressForm(forms.Form):

    full_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    phone_no = forms.CharField(max_length=10, required=True)
    district = forms.CharField(max_length=100, required=True)
    state = forms.CharField(max_length=100, required=True)
    city = forms.CharField(max_length=100, required=True)
    address_field = forms.CharField(required=True)
    pincode = forms.CharField(max_length=10, required=True)

    def clean_phone_no(self):
        phone = self.cleaned_data.get("phone_no")
        if phone and (not phone.isdigit() or len(phone) != 10):
            validationerror("Phone number must be exactly 10 digits")
        else:
            return phone
        
    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")
        print("signup email:",full_name)
        if not re.match(r'^[A-Za-z\s]+$', full_name):
            validationerror("Name can contain only alphabets and spaces.")
        else:
            return full_name
        
    def clean_address_field(self):
        address_field = self.cleaned_data.get("address_field")
        if not address_field.replace(" ", "").isalpha():
            validationerror("Address can contain only alphabets and spaces.")
        else:
            return address_field
    