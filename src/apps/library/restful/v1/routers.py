from django.urls import path
from .biblio import views

urlpatterns = [
    path("biblios/", views.BiblioList.as_view(), name="biblio-list"),
]
