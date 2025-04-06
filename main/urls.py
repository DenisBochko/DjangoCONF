from django.urls import path
from .views import *

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update', UserUpdateView.as_view(), name='profile_update'),

    path('meeting_create/', MeetingCreateView.as_view(), name='meeting_create'),
    path('meeting_list/', MeetingListView.as_view(), name='meeting_list'),
    path('agenda_create/', AgendaCreateView.as_view(), name='agenda_create'),
    path('agenda_get/', AgendasView.as_view(), name='agenda_get'),
    path('vote_create/', VoteCreateView.as_view(), name='vote_create'),
    path('vote_update/', VoteUpdateView.as_view(), name='vote_update'),

    path('generate-protocol/<int:agenda_item_id>/', GenerateProtocolView.as_view(), name='generate-protocol'),

    path('check_token/', CheckAuthToken.as_view(), name='check_token'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
