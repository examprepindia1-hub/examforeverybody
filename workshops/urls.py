from django.urls import path
from .views import WorkshopAccessView

app_name = 'workshops'

urlpatterns = [
    path('<slug:slug>/access/', WorkshopAccessView.as_view(), name='workshop_access'),
]
