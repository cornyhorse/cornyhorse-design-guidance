from django.conf import settings


def site(request):
    return {"product_name": settings.SITE_NAME}
