from django.conf.urls import url
import views

urlpatterns = [
    url(r'^check/raise/500/$',
        view=views.raiseerror,
        name='check_raise'),

    url(r'^check/raise/404/$',
        view=views.raise404,
        name='check_raise'),

    url(r'^check/404/$',
        view=views.notfound,
        name='check_raise'),
]
