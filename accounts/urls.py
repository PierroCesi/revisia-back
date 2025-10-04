from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('subscription-info/', views.get_subscription_info, name='subscription_info'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('role-info/', views.user_role_info, name='user_role_info'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/', views.get_documents, name='get_documents'),
    path('documents/<int:document_id>/questions/', views.get_questions, name='get_questions'),
    path('lessons/', views.get_lessons, name='get_lessons'),
    path('lessons/create/', views.create_lesson, name='create_lesson'),
    path('lessons/<int:lesson_id>/', views.get_lesson, name='get_lesson'),
    path('lessons/<int:lesson_id>/submit-answer/', views.submit_answer, name='submit_answer'),
    path('lessons/<int:lesson_id>/reset/', views.reset_lesson, name='reset_lesson'),
    path('lessons/<int:lesson_id>/attempts/', views.get_lesson_attempts, name='get_lesson_attempts'),
    path('lessons/<int:lesson_id>/guest-results/', views.get_guest_quiz_results, name='get_guest_quiz_results'),
    path('lessons/<int:lesson_id>/delete/', views.delete_lesson, name='delete_lesson'),
    path('lessons/stats/', views.get_lesson_stats, name='get_lesson_stats'),
    path('transfer-guest-data/', views.transfer_guest_data, name='transfer_guest_data'),
    # Stripe endpoints
    path('stripe/create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('stripe/confirm-payment/', views.confirm_payment, name='confirm_payment'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
