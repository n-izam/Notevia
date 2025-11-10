from django.contrib import messages
from django.core.exceptions import ValidationError
from accounts.models import UserProfile
from django.shortcuts import get_object_or_404


# message notification

def success_notify(request, msg="Action completed successfully!"):
    messages.success(request, msg)

def error_notify(request, msg="Something went wrong"):
    messages.error(request, msg)

def warning_notify(request, msg="invalid cridentials"):
    messages.warning(request, msg)

def info_notify(request, msg="here is some info"):
    messages.info(request, msg)

# validation error

def validationerror(msg="invalid cridentials"):
    raise ValidationError(msg)

def profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    return profile

def referral_amount():
    amount = 400
    return amount