from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.conf.urls import url, include

from .views import RegisterView, ResendActivationEmailView, ActivationView, LoginView, DashboardView, ForgotPasswordView, LogoutView, ChangeUserPasswordView, ChangeUserDetailsView


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^register$', RegisterView.as_view(), name='register'),
    url(r'^resend-activation-email$', ResendActivationEmailView.as_view(), name='resend-activation-email'),
    url(r'^activation/(?P<token>.*)', ActivationView.as_view(), name='activation'),
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'^forgot-password$', ForgotPasswordView.as_view(), name='forgot-password'),  
    url(r'^profile-dashboard$', login_required(DashboardView.as_view()), name='profile-dashboard'),    
    url(r'^logout$', LogoutView.as_view(), name='logout'),
    url(r'^change-password$',login_required(ChangeUserPasswordView.as_view()), name='change-password'),
    url(r'^change-user-details$',login_required(ChangeUserDetailsView.as_view()), name='change-user-details'),
    
    
]