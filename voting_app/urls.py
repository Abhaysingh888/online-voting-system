from django.urls import path
from . import views

urlpatterns = [
    path('',               views.home_view,            name='home'),
    path('login/',         views.login_view,            name='login'),
    path('register/',      views.register_view,         name='register'),
    path('logout/',        views.logout_view,           name='logout'),
    path('dashboard/',     views.dashboard_view,        name='dashboard'),
    path('vote/',          views.vote_view,             name='vote'),
    path('results/',       views.results_view,          name='results'),
    path('forgot/',        views.forgot_password_view,  name='forgot_password'),
     path('about/', views.about, name='about'),
]