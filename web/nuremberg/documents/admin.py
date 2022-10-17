from django.contrib import admin

from .models import Document, DocumentImage


class DocumentImageInline(admin.TabularInline):
    model = DocumentImage
    fields = ('page_number', 'physical_page_number', 'url')
    readonly_fields = fields
    extra = 0


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'image_count')
    inlines = [DocumentImageInline]
    readonly_fields = ('updated_at',)


admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentImage)
