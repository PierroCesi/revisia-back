from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'education_level', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'education_level', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations éducatives', {'fields': ('education_level',)}),
    )

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at', 'user')
    search_fields = ('title', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'document', 'lesson', 'question_type', 'difficulty', 'created_at')
    list_filter = ('question_type', 'difficulty', 'created_at', 'document__user')
    search_fields = ('question_text', 'document__title', 'document__user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('answer_text', 'question', 'is_correct')
    list_filter = ('is_correct', 'question__question_type', 'question__document__user')
    search_fields = ('answer_text', 'question__question_text', 'question__document__title')
    ordering = ('question', 'id')

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'document', 'difficulty', 'total_questions', 'completed_questions', 'score', 'last_score', 'total_attempts', 'average_score', 'status', 'last_accessed')
    list_filter = ('difficulty', 'status', 'created_at', 'last_accessed', 'user')
    search_fields = ('title', 'user__email', 'document__title')
    readonly_fields = ('created_at', 'last_accessed', 'total_questions', 'completed_questions', 'score', 'last_score', 'total_attempts', 'average_score')
    ordering = ('-last_accessed',)

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'lesson', 'selected_answer', 'open_answer', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at', 'lesson__user')
    search_fields = ('user__email', 'question__question_text', 'lesson__title')
    readonly_fields = ('answered_at',)
    ordering = ('-answered_at',)

@admin.register(LessonAttempt)
class LessonAttemptAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'attempt_number', 'score', 'completed_at')
    list_filter = ('completed_at', 'lesson__user')
    search_fields = ('lesson__title', 'lesson__user__email')
    readonly_fields = ('completed_at',)
    ordering = ('-completed_at',)

# Configuration du site admin
admin.site.site_header = "Administration Révisia"
admin.site.site_title = "Révisia Admin"
admin.site.index_title = "Gestion de la plateforme Révisia"
