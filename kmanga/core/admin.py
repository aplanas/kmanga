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


class SourceAdmin(admin.ModelAdmin):
    inlines = [SourceLanguageInline, GenreInline]


admin.site.register(Source, SourceAdmin)
# admin.site.register(ConsolidateGenre)


class IssueAdmin(admin.StackedInline):
    model = Issue


class MangaAdmin(admin.ModelAdmin):
    inlines = [IssueAdmin]


admin.site.register(Manga, MangaAdmin)


class SubscriptionAdmin(admin.ModelAdmin):
    model = Subscription


admin.site.register(Subscription, SubscriptionAdmin)


class HistoryAdmin(admin.ModelAdmin):
    model = History


admin.site.register(History, HistoryAdmin)
