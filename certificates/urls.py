from django.urls import path
from .views import DownloadCertificateView

app_name = 'certificates'

urlpatterns = [
    path('download/<slug:slug>/', DownloadCertificateView.as_view(), name='download'),
]
