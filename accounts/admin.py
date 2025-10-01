from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'get_user_role_display', 'is_premium', 'premium_expires_at', 'quiz_count_today', 'attempts_count_today', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_premium', 'education_level', 'date_joined', 'premium_expires_at')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations éducatives', {'fields': ('education_level',)}),
        ('Statut Premium', {
            'fields': ('is_premium', 'premium_expires_at'),
            'description': 'Gestion du statut premium de l\'utilisateur'
        }),
        ('Limites quotidiennes', {
            'fields': ('quiz_count_today', 'last_quiz_date', 'attempts_count_today', 'last_attempt_date'),
            'description': 'Suivi des limites quotidiennes (reset automatique)',
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('quiz_count_today', 'last_quiz_date', 'attempts_count_today', 'last_attempt_date')
    
    def get_user_role_display(self, obj):
        """Affiche le rôle de l'utilisateur avec des couleurs"""
        role = obj.get_user_role()
        if role == 'premium':
            return f'<span style="color: #f59e0b; font-weight: bold;">⭐ Premium</span>'
        elif role == 'free':
            return f'<span style="color: #10b981; font-weight: bold;">🆓 Gratuit</span>'
        else:
            return f'<span style="color: #6b7280;">👤 Invité</span>'
    get_user_role_display.short_description = 'Rôle'
    get_user_role_display.allow_tags = True
    
    def get_queryset(self, request):
        """Optimise les requêtes pour les champs calculés"""
        return super().get_queryset(request).select_related()

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'get_user_role', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at', 'user__is_premium')
    search_fields = ('title', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def get_user_role(self, obj):
        """Affiche le rôle de l'utilisateur propriétaire du document"""
        role = obj.user.get_user_role()
        if role == 'premium':
            return f'<span style="color: #f59e0b; font-weight: bold;">⭐ Premium</span>'
        elif role == 'free':
            return f'<span style="color: #10b981; font-weight: bold;">🆓 Gratuit</span>'
        else:
            return f'<span style="color: #6b7280;">👤 Invité</span>'
    get_user_role.short_description = 'Rôle utilisateur'
    get_user_role.allow_tags = True

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
    list_display = ('title', 'user', 'get_user_role', 'document', 'difficulty', 'total_questions', 'completed_questions', 'score', 'last_score', 'total_attempts', 'average_score', 'status', 'last_accessed')
    list_filter = ('difficulty', 'status', 'created_at', 'last_accessed', 'user__is_premium')
    search_fields = ('title', 'user__email', 'document__title')
    readonly_fields = ('created_at', 'last_accessed', 'total_questions', 'completed_questions', 'score', 'last_score', 'total_attempts', 'average_score')
    ordering = ('-last_accessed',)
    
    def get_user_role(self, obj):
        """Affiche le rôle de l'utilisateur propriétaire de la leçon"""
        role = obj.user.get_user_role()
        if role == 'premium':
            return f'<span style="color: #f59e0b; font-weight: bold;">⭐ Premium</span>'
        elif role == 'free':
            return f'<span style="color: #10b981; font-weight: bold;">🆓 Gratuit</span>'
        else:
            return f'<span style="color: #6b7280;">👤 Invité</span>'
    get_user_role.short_description = 'Rôle utilisateur'
    get_user_role.allow_tags = True

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_user_role', 'question', 'lesson', 'selected_answer', 'open_answer', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at', 'lesson__user__is_premium')
    search_fields = ('user__email', 'question__question_text', 'lesson__title')
    readonly_fields = ('answered_at',)
    ordering = ('-answered_at',)
    
    def get_user_role(self, obj):
        """Affiche le rôle de l'utilisateur qui a répondu"""
        role = obj.user.get_user_role()
        if role == 'premium':
            return f'<span style="color: #f59e0b; font-weight: bold;">⭐ Premium</span>'
        elif role == 'free':
            return f'<span style="color: #10b981; font-weight: bold;">🆓 Gratuit</span>'
        else:
            return f'<span style="color: #6b7280;">👤 Invité</span>'
    get_user_role.short_description = 'Rôle utilisateur'
    get_user_role.allow_tags = True

@admin.register(LessonAttempt)
class LessonAttemptAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'get_user_role', 'attempt_number', 'score', 'completed_at')
    list_filter = ('completed_at', 'lesson__user__is_premium')
    search_fields = ('lesson__title', 'lesson__user__email')
    readonly_fields = ('completed_at',)
    ordering = ('-completed_at',)
    
    def get_user_role(self, obj):
        """Affiche le rôle de l'utilisateur propriétaire de la tentative"""
        role = obj.lesson.user.get_user_role()
        if role == 'premium':
            return f'<span style="color: #f59e0b; font-weight: bold;">⭐ Premium</span>'
        elif role == 'free':
            return f'<span style="color: #10b981; font-weight: bold;">🆓 Gratuit</span>'
        else:
            return f'<span style="color: #6b7280;">👤 Invité</span>'
    get_user_role.short_description = 'Rôle utilisateur'
    get_user_role.allow_tags = True

# Configuration du site admin
admin.site.site_header = "Administration Révisia"
admin.site.site_title = "Révisia Admin"
admin.site.index_title = "Gestion de la plateforme Révisia"
