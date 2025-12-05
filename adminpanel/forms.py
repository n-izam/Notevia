from django import forms
# from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re
from accounts.utils import validationerror
from django.utils import timezone
from datetime import datetime


class OfferForm(forms.Form):

    offer_title = forms.CharField(max_length=255, required=True)
    discount = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    about = forms.CharField(required=True)
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=True)

    def clean_start_date(self):
        today = timezone.now().date()
        start_date = self.cleaned_data.get('start_date')
        # start_date = start_date.date()
        if not start_date >= today:
            validationerror('Start date must be greater than equal to today ' )
        else:
            return start_date
    
    def clean_end_date(self):
        today = timezone.now().date()
        end_date = self.cleaned_data.get('end_date')
        if not end_date > today:
            validationerror('End date must be greater than today' )
            
        else:
            return end_date
        
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount <= 0:
            validationerror("discount must be a positive number")
        else:
            return discount
        
class VariantForm(forms.Form):
    

    name = forms.CharField(max_length=255, required=True)
    description = forms.CharField(required=True)
    price = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    discount_percent = forms.DecimalField(max_digits=5, decimal_places=2, required=True)
    stock = forms.IntegerField(required=True)


    def clean_discount_percent(self):
        discount_percent = self.cleaned_data.get('discount_percent')

        if not re.match(r'^(100(\.00?)?|[0-9]?\d(\.\d{1,2})?)$', str(discount_percent)):
                validationerror('Variant percentage must be a valid number (e.g., 0 to 100.00) or 0.')
        else:
            return discount_percent
        
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name.replace(" ", "").isalpha():
            validationerror('Variant name can contain only alphabets and spaces.')
                
        elif  len(name) < 4:
            validationerror('proper Variant name needed more character')
            
        else:
            return name
        
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock <= 0:
            validationerror("stock must be a positive number")
        else:
            return stock
        
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            validationerror("stock must be a positive number")
        else:
            return price
        

class CategoryForm(forms.Form):
    
    name = forms.CharField(max_length=255, required=True)
    description = forms.CharField(required=True)

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name.replace(" ", "").isalpha():
            validationerror("Category name can contain only alphabets and spaces.")
        else:
            return name
        
    