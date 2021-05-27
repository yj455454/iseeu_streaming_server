from django.contrib import admin
from django.urls import path
from mjpeg.views import *

urlpatterns = [
    path('<device_id>', stream),
]