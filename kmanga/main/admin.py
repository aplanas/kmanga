from django.contrib import admin

from .models import Source
from .models import SourceLanguage
# from .models import ConsolidateGenre
from .models import Genre
from .models import Manga
from .models import Issue


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
