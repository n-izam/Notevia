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

def custom_page_range(current_page, total_pages):
    pages = []

    # Always show first 3 pages
    for p in range(1, min(4, total_pages + 1)):
        pages.append(p)

    # Add ellipsis if current_page is far from first 3
    if current_page > 4:
        if pages[-1] != "...":
            pages.append("...")

    # Pages around current page (current -1, current, current +1)
    for p in range(current_page - 1, current_page + 2):
        if p > 3 and p < total_pages - 1:  # avoid duplicating first 3 or last 2
            pages.append(p)

    # Add ellipsis if current_page is far from last 2
    if current_page < total_pages - 3:
        if pages[-1] != "...":
            pages.append("...")

    # Always show last 2 pages
    if total_pages > 3:
        pages.extend([total_pages - 1, total_pages])

    # Remove duplicates and sort
    final_pages = []
    for p in pages:
        if p not in final_pages:
            final_pages.append(p)

    return final_pages