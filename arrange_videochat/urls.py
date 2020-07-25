from django.urls import path
from . import views

app_name = "arrange_videochat"

urlpatterns = [
    path("", views.EventList.as_view(), name="list"),
    path("host", views.EventHost.as_view(), name="host"),
    path("hosted/<int:pk>", views.EventHostConfirmation.as_view(), name="hosted"),
    path("participate/<int:pk>", views.EventJoin.as_view(), name="participate"),
    path(
        "participated/<int:pk>",
        views.EventJoinConfirmation.as_view(),
        name="participated",
    ),
    path("leave/<uuid:uuid>", views.EventLeaveView.as_view(), name="leave",),
    path("delete/<uuid:uuid>", views.EventDeleteView.as_view(), name="delete"),
]
