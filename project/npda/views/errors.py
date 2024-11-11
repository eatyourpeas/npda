from django.shortcuts import render

from django.core.exceptions import SuspiciousOperation


def error_400(request, exception):
    context = {}
    return render(
        request=request, template_name="errors/400.html", context=context, status=400
    )


def error_403(request, exception):
    context = {}
    return render(
        request=request, template_name="errors/403.html", context=context, status=403
    )


def error_404(request, exception):
    context = {}
    return render(
        request=request, template_name="errors/404.html", context=context, status=404
    )


def error_500(request):
    context = {}
    return render(
        request=request, template_name="errors/500.html", context=context, status=500
    )


def csrf_fail(request, reason=""):
    context = {}
    return render(
        request=request,
        template_name="errors/csrf_fail.html",
        context=context,
        status=403,
    )
