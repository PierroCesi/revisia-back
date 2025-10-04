from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt, GuestSession, StripePayment

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'get_user_role_display', 'get_subscription_status_display', 'is_premium', 'subscription_status', 'get_cancel_status_display', 'subscription_interval', 'current_period_end', 'quiz_count_today', 'attempts_count_today', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_premium', 'education_level', 'date_joined', 'cancel_at_period_end', 'subscription_status')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations éducatives', {'fields': ('education_level',)}),
        ('Abonnement Premium', {
            'fields': ('is_premium', 'stripe_customer_id', 'stripe_subscription_id', 'subscription_status', 'subscription_interval', 'current_period_end', 'cancel_at_period_end', 'canceled_at', 'get_subscription_status_display', 'get_cancel_status_display'),
            'description': 'Gestion de l\'abonnement premium de l\'utilisateur'
        }),
        ('Limites quotidiennes', {
            'fields': ('quiz_count_today', 'last_quiz_date', 'attempts_count_today', 'last_attempt_date'),
            'description': 'Suivi des limites quotidiennes (reset automatique)',
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('quiz_count_today', 'last_quiz_date', 'attempts_count_today', 'last_attempt_date', 'get_subscription_status_display', 'get_cancel_status_display', 'stripe_customer_id', 'stripe_subscription_id')
    
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
    
    def get_subscription_status_display(self, obj):
        """Affiche le statut de l'abonnement avec des couleurs"""
        status = obj.get_subscription_status()
        if status == 'active':
            return f'<span style="color: #10b981; font-weight: bold;">✅ Actif</span>'
        elif status == 'expired':
            return f'<span style="color: #dc2626; font-weight: bold;">❌ Expiré</span>'
        elif status == 'permanent':
            return f'<span style="color: #7c3aed; font-weight: bold;">♾️ Permanent</span>'
        else:
            return f'<span style="color: #6b7280;">⚪ Inactif</span>'
    get_subscription_status_display.short_description = 'Statut Abonnement'
    get_subscription_status_display.allow_tags = True
    
    def get_cancel_status_display(self, obj):
        """Affiche le statut d'annulation"""
        if obj.cancel_at_period_end:
            if obj.current_period_end:
                from django.utils import timezone
                now = timezone.now()
                if obj.current_period_end > now:
                    delta = obj.current_period_end - now
                    return f'<span style="color: #f59e0b; font-weight: bold;">🚫 Annulé dans {delta.days} jours</span>'
                else:
                    return f'<span style="color: #dc2626; font-weight: bold;">❌ Expiré</span>'
            else:
                return f'<span style="color: #f59e0b; font-weight: bold;">🚫 Annulé</span>'
        elif obj.subscription_status == 'canceled':
            return f'<span style="color: #dc2626; font-weight: bold;">❌ Annulé</span>'
        else:
            return f'<span style="color: #10b981;">✅ Actif</span>'
    get_cancel_status_display.short_description = 'Statut Annulation'
    get_cancel_status_display.allow_tags = True
    
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

@admin.register(GuestSession)
class GuestSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'ip_address', 'documents_created', 'is_blocked', 'last_activity', 'transferred_to_user', 'transferred_at')
    list_filter = ('is_blocked', 'transferred_at', 'created_at', 'last_activity')
    search_fields = ('session_id', 'ip_address', 'transferred_to_user__email')
    readonly_fields = ('created_at', 'last_activity', 'transferred_at')
    ordering = ('-last_activity',)
    
    fieldsets = (
        ('Informations de session', {
            'fields': ('session_id', 'ip_address', 'documents_created', 'is_blocked')
        }),
        ('Activité', {
            'fields': ('created_at', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('Transfert', {
            'fields': ('transferred_to_user', 'transferred_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_intent_id', 'user_email', 'amount_display', 'status_display', 'is_successful_display', 'created_at')
    list_filter = ('status', 'currency', 'created_at', 'user__is_premium')
    search_fields = ('payment_intent_id', 'user__email', 'user__username')
    readonly_fields = ('payment_intent_id', 'created_at', 'updated_at', 'amount_euros', 'is_successful')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de paiement', {
            'fields': ('payment_intent_id', 'user', 'amount', 'amount_euros', 'currency', 'status', 'is_successful')
        }),
        ('Métadonnées', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Affiche l'email de l'utilisateur"""
        return obj.user.email
    user_email.short_description = 'Utilisateur'
    user_email.admin_order_field = 'user__email'
    
    def amount_display(self, obj):
        """Affiche le montant avec formatage"""
        return f"{obj.amount_euros:.2f} €"
    amount_display.short_description = 'Montant'
    amount_display.admin_order_field = 'amount'
    
    def status_display(self, obj):
        """Affiche le statut avec des couleurs"""
        if obj.status == 'succeeded':
            return f'<span style="color: #10b981; font-weight: bold;">✅ Réussi</span>'
        elif obj.status == 'requires_payment_method':
            return f'<span style="color: #f59e0b; font-weight: bold;">⚠️ Paiement requis</span>'
        elif obj.status == 'requires_confirmation':
            return f'<span style="color: #3b82f6; font-weight: bold;">🔄 Confirmation requise</span>'
        elif obj.status == 'canceled':
            return f'<span style="color: #dc2626; font-weight: bold;">❌ Annulé</span>'
        else:
            return f'<span style="color: #6b7280;">{obj.status}</span>'
    status_display.short_description = 'Statut'
    status_display.allow_tags = True
    status_display.admin_order_field = 'status'
    
    def is_successful_display(self, obj):
        """Affiche si le paiement est réussi"""
        if obj.is_successful:
            return f'<span style="color: #10b981; font-weight: bold;">✅ Oui</span>'
        else:
            return f'<span style="color: #dc2626; font-weight: bold;">❌ Non</span>'
    is_successful_display.short_description = 'Réussi'
    is_successful_display.allow_tags = True
    is_successful_display.admin_order_field = 'is_successful'

# Configuration du site admin
admin.site.site_header = "Administration Révisia"
admin.site.site_title = "Révisia Admin"
admin.site.index_title = "Gestion de la plateforme Révisia"
