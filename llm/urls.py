"""
URL configuration for llm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home, name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),  # Main chat interface
    path("dashboard/", views.dashboard, name="dashboard"),  # Chat history dashboard
    path(
        "conversation/<str:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),  # Individual conversation view
    path(
        "api/conversations/", views.api_conversations, name="api_conversations"
    ),  # API endpoint for conversations
    path(
        "api/delete-conversation/",
        views.delete_conversation_ajax,
        name="delete_conversation_ajax",
    ),  # AJAX delete endpoint
]
