from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('auth/', include('users.urls', namespace='users')),
    path('about/', include('about.urls', namespace='about')),
    path('', include('posts.urls', namespace='posts')),
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls'))
]
