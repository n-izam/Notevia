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
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if not user_profile.image:
        profile = "https://res.cloudinary.com/dbufuuut7/image/upload/v1764074718/generated-image_6_i7qd7r.jpg"
    else:
        profile = user_profile.image.url
        
    return profile

def referral_amount():
    amount = 400
    return amount

def custom_page_range(page, total_pages):
    pages = []

    # Always show first 3 pages: 1,2,3
    for p in range(1, min(4, total_pages + 1)):
        pages.append(p)

    # Add ... if current page > 5
    if page > 5:
        pages.append("...")

    # Middle page (current page only, optional)
    if 4 < page < total_pages - 2:
        pages.append(page)

    # Add ... if current page < total_pages - 3
    if page < total_pages - 3:
        pages.append("...")

    # Always show last 2 pages
    if total_pages > 3:
        pages.extend([total_pages - 1, total_pages])

    # Remove duplicates
    return list(dict.fromkeys(pages))