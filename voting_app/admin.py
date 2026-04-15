from django.contrib import admin
from .models import Candidate, Vote, Election


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display  = ('name', 'party', 'votes')
    list_filter   = ('party',)
    search_fields = ('name', 'party')
    ordering      = ('-votes',)
    readonly_fields = ('votes',)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display    = ('user', 'candidate', 'timestamp')
    list_filter     = ('candidate',)
    search_fields   = ('user__username', 'candidate__name')
    readonly_fields = ('user', 'candidate', 'timestamp')
    ordering        = ('-timestamp',)


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display  = ('title', 'start_time', 'end_time', 'is_active', 'status_label')
    list_filter   = ('is_active',)
    search_fields = ('title',)

    def status_label(self, obj):
        status = obj.status_label()
        icons  = {'upcoming': '⏳ Upcoming', 'ongoing': '🟢 Ongoing', 'ended': '🔴 Ended'}
        return icons.get(status, status)
    status_label.short_description = 'Status'