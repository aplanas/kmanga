from django.contrib import admin

from .models import Source
from .models import SourceLanguage
# from .models import ConsolidateGenre
from .models import Genre
from .models import Manga
from .models import Issue
from .models import Result
from .models import Subscription


class SourceLanguageInline(admin.StackedInline):
    model = SourceLanguage


class GenreInline(admin.StackedInline):
    model = Genre


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'spider', 'url')
    inlines = (SourceLanguageInline, GenreInline)


# @admin.register(ConsolidateGenre)
# class ConsolidateGenreAdmin(admin.ModelAdmin):
#     pass


class IssueInline(admin.StackedInline):
    model = Issue


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'source', 'url')
    list_filter = ('source',)
    inlines = (IssueInline,)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('manga', 'source', 'user', 'issues_per_day',
                    'language', 'paused', 'modified')
    raw_id_fields = ('manga', 'user')
    date_hierarchy = 'modified'

    def source(self, subscription):
        return subscription.manga.source
    source.short_description = 'Source'
    source.admin_order_field = 'manga__source'


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('issue', 'subscription', 'user', 'status', 'retry',
                    'created')
    list_filter = ('status',)
    raw_id_fields = ('issue', 'subscription')
    date_hierarchy = 'modified'

    def user(self, result):
        return result.subscription.user
    user.short_description = 'User'
    user.admin_order_field = 'subscription__user'
