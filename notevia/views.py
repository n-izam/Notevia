from django.views import View
from django.shortcuts import render
from django.http import HttpResponseNotFound

class Custom404View(View):

    def get(self, request, exception=None, *args, **kwargs):

        if request.user.is_authenticated and request.user.is_superuser:
            return HttpResponseNotFound(render(request, '404_admin.html', status=404))
            # return render(request, "404_admin.html", status=404)
        else:
            return HttpResponseNotFound(render(request, '404_user.html', status=404))
            # return render(request, "404_user.html", status=404)
        
        