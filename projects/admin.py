from django.contrib import admin
from .models import Project, Task, Comment

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_by', 'created_at', 'progress_display')
    list_filter = ('status',)
    search_fields = ('name', 'description')

    def progress_display(self, obj):
        return f"{obj.progress()}%"
    progress_display.short_description = 'Progress'

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'assigned_to', 'due_date')
    list_filter = ('status', 'project')
    search_fields = ('title', 'description')

admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Comment)