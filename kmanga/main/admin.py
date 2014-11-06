from django.contrib import admin

from main.models import Source, SourceLanguage, ConsolidateGenre, Genre
from main.models import Manga, Issue

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
