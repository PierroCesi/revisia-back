from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/', views.get_documents, name='get_documents'),
    path('documents/<int:document_id>/questions/', views.get_questions, name='get_questions'),
    path('lessons/', views.get_lessons, name='get_lessons'),
    path('lessons/create/', views.create_lesson, name='create_lesson'),
    path('lessons/<int:lesson_id>/', views.get_lesson, name='get_lesson'),
    path('lessons/<int:lesson_id>/submit-answer/', views.submit_answer, name='submit_answer'),
    path('lessons/<int:lesson_id>/reset/', views.reset_lesson, name='reset_lesson'),
    path('lessons/<int:lesson_id>/attempts/', views.get_lesson_attempts, name='get_lesson_attempts'),
    path('lessons/stats/', views.get_lesson_stats, name='get_lesson_stats'),
]
