from django.contrib import admin
from .models import *

admin.site.register(UserProfile)

admin.site.register(Meeting)
admin.site.register(UserMeetings)
admin.site.register(AgendaItem)
admin.site.register(Vote)
