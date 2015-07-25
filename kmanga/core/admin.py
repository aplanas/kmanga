from django.contrib import admin

from .models import Source
from .models import SourceLanguage
# from .models import ConsolidateGenre
from .models import Genre
from .models import Manga
from .models import Issue
from .models import Subscription
from .models import History


class SourceLanguageInline(admin.StackedInline):
    model = SourceLanguage


class GenreInline(admin.StackedInline):
    model = Genre


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    inlines = [SourceLanguageInline, GenreInline]


# @admin.register(ConsolidateGenre)
# class ConsolidateGenreAdmin(admin.ModelAdmin):
#     pass


class IssueAdmin(admin.StackedInline):
    model = Issue


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    inlines = [IssueAdmin]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    pass


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    date_hierarchy = 'modified'
