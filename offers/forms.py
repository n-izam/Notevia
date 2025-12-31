from django import forms
# from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re
from accounts.utils import validationerror
from django.utils import timezone
from datetime import datetime




class CouponForm(forms.Form):

    coupon_name = forms.CharField(max_length=50, required=True)
    limit = forms.IntegerField(required=True)
    max_price = forms.DecimalField(max_digits=10, required=True, decimal_places=2)
    minpurchase = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    discount = forms.IntegerField(required=True)
    start_date = forms.DateTimeField(required=True)
    end_date = forms.DateTimeField(required=True)

    

    def clean_minpurchase(self):
        minpurchase = self.cleaned_data.get("minpurchase")
        if minpurchase is not None and minpurchase <= 0:
            validationerror("Minimum purchase must be a positive number.")
        return minpurchase

    def clean_start_date(self):
        today = timezone.now().date()
        start_date = self.cleaned_data.get('start_date')
        start_date = start_date.date()
        if not start_date >= today:
            validationerror('Start date must be greater than equal to today ' )
        else:
            return start_date
    
    def clean_end_date(self):
        today = timezone.now().date()
        end_date = self.cleaned_data.get('end_date')
        end_date = end_date.date()
        if not end_date > today:
            validationerror('End date must be greater than today' )
            
        else:
            return end_date
        
    def clean_limit(self):
        limit = self.cleaned_data.get('limit')
        if limit <= 0:
            validationerror("limit must be a positive number")
        else:
            return limit
    
    def clean_max_price(self):
        max_price = self.cleaned_data.get('max_price')
        if max_price <= 0:
            validationerror("max redeemable price must be a positive number")
        else:
            return max_price
    
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount <= 0:
            validationerror("discount must be a positive number")
        # elif not re.match(r'^(100(\.00?)?|[0-9]?\d(\.\d{1,2})?)$', str(discount)):
        elif not re.match(r'^(80(\.00?)?|[0-7]?\d(\.\d{1,2})?)$', str(discount)):
                validationerror('Coupon percentage must be a valid number (e.g., 1 to 80.00)')
        else:
            return discount
        
    # def clean_minimun_purchase(self):
    #     minpurchase = self.cleaned_data.get('minpurchase')
    #     max_price = self.cleaned_data.get('max_price')
    #     if not minpurchase >= max_price:
    #         validationerror("minimun purchase must be greater than maximum redeemable price")
    #     else:
    #         return minpurchase
