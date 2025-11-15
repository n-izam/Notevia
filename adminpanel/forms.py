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
        
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount <= 0:
            validationerror("discount must be a positive number")
        else:
            return discount