from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
     # New project detail URL
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('project/<int:pk>/edit/', views.project_edit, name='project_edit'),
    
    # Task URLs
    path('project/<int:project_pk>/task/create/', views.task_create, name='task_create'),
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),
    
    # Comment URL
    path('task/<int:task_pk>/comment/', views.comment_create, name='comment_create'),
]