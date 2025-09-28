from django.views import View
from django.shortcuts import render

class Custom404View(View):

    def get(self, request, exception=None, *args, **kwargs):

        if request.user.is_authenticated and request.user.is_superuser:
            return render(request, "404_admin.html", status=404)
        else:
            return render(request, "404_user.html", status=404)