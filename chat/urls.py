from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/chats/", views.get_chats, name="get_chats"),
    path("api/chats/new/", views.create_chat, name="create_chat"),
    path("accounts/", include("allauth.urls")), # Auth URLs
    path("api/chats/<int:chat_id>/", views.get_chat_details, name="chat_details"),
    path("api/chats/<int:chat_id>/rename/", views.rename_chat, name="rename_chat"),
    path("api/chats/<int:chat_id>/delete/", views.delete_chat, name="delete_chat"),
    path("api/chats/<int:chat_id>/message/", views.send_message, name="send_message"),
 
]



