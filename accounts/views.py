from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import os
import uuid
import logging

logger = logging.getLogger(__name__)
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer, 
    DocumentSerializer, QuestionSerializer, LessonSerializer, 
    UserAnswerSerializer, LessonStatsSerializer, LessonAttemptSerializer
)
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt, GuestSession
from ai_service import OpenAIService

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Met à jour le profil de l'utilisateur"""
    user = request.user
    
    # Mettre à jour les champs autorisés
    allowed_fields = ['first_name', 'last_name', 'username', 'education_level']
    
    for field in allowed_fields:
        if field in request.data:
            setattr(user, field, request.data[field])
    
    try:
        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Erreur lors de la mise à jour du profil'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def user_role_info(request):
    """Retourne les informations de rôle de l'utilisateur"""
    user = request.user if request.user.is_authenticated else None
    session_id = request.GET.get('session_id')
    
    if user:
        role = user.get_user_role()
        can_create_quiz = user.can_create_quiz_today()
        can_attempt_quiz = user.can_attempt_quiz_today()
        quiz_count_today = user.quiz_count_today
        attempts_count_today = user.attempts_count_today
        guest_session = None
    else:
        role = 'guest'
        # Vérifier la session invité
        from .guest_utils import get_or_create_guest_session
        try:
            guest_session = get_or_create_guest_session(request, session_id)
            can_create_quiz = guest_session.can_create_document()
            can_attempt_quiz = True
            quiz_count_today = guest_session.documents_created
            attempts_count_today = 0
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la session invité: {e}")
            can_create_quiz = False
            can_attempt_quiz = False
            quiz_count_today = 0
            attempts_count_today = 0
            guest_session = None
    
    # Définir les limites selon le rôle
    limits = {
        'guest': {
            'max_questions': 5,
            'max_quizzes_per_day': 1,
            'max_attempts_per_quiz': 1,
            'can_save_results': False
        },
        'free': {
            'max_questions': 6,
            'max_quizzes_per_day': 1,
            'max_attempts_per_day': 2,
            'can_save_results': True
        },
        'premium': {
            'max_questions': None,  # None = illimité
            'max_quizzes_per_day': None,  # None = illimité
            'max_attempts_per_day': None,  # None = illimité
            'can_save_results': True
        }
    }
    
    response_data = {
        'role': role,
        'can_create_quiz': can_create_quiz,
        'can_attempt_quiz': can_attempt_quiz,
        'quiz_count_today': quiz_count_today,
        'attempts_count_today': attempts_count_today,
        'limits': limits[role],
        'user': UserSerializer(user).data if user else None
    }
    
    # Ajouter les informations de session pour les invités
    if role == 'guest' and guest_session:
        response_data['session_id'] = guest_session.session_id
        response_data['remaining_uses'] = max(0, 1 - guest_session.documents_created)
        response_data['is_blocked'] = guest_session.is_blocked
        response_data['session_expires_at'] = guest_session.created_at + timezone.timedelta(hours=24)
    
    return Response(response_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    # Logout simple - le frontend supprime les tokens du localStorage
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])  # Permet aux guests
def upload_document(request):
    if 'file' not in request.FILES:
        return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    title = request.data.get('title', file.name)
    
    # Récupérer les paramètres IA
    question_count = int(request.data.get('question_count', 5))
    difficulty = request.data.get('difficulty', 'medium')
    question_types = request.data.get('question_types', '["qcm"]')
    education_level = request.data.get('education_level', '')
    instructions = request.data.get('instructions', '')
    session_id = request.data.get('session_id')  # ID de session pour les invités
    
    # Vérifier les limites selon le rôle utilisateur
    user = request.user if request.user.is_authenticated else None
    user_role = user.get_user_role() if user else 'guest'
    
    # Vérifications spécifiques pour les invités
    if user_role == 'guest':
        from .guest_utils import check_guest_limits, rate_limit_check
        
        # Vérifier le rate limiting par IP (5 requêtes par heure)
        is_rate_allowed, remaining_requests = rate_limit_check(request, max_requests=5, window_minutes=60)
        if not is_rate_allowed:
            return Response({
                'error': 'Trop de requêtes',
                'details': 'Vous avez dépassé la limite de requêtes. Veuillez attendre avant de réessayer.',
                'action': 'rate_limit_exceeded'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Vérifier les limites de session invité
        is_allowed, guest_session, error_msg = check_guest_limits(request, session_id)
        if not is_allowed:
            return Response(error_msg, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier les limites de questions pour les invités
        if question_count > 5:
            return Response({
                'error': 'Limite atteinte. Les utilisateurs non connectés sont limités à 5 questions maximum.',
                'details': 'Inscrivez-vous gratuitement pour créer des quiz avec plus de questions et sauvegarder vos résultats.',
                'action': 'signup_required'
            }, status=status.HTTP_403_FORBIDDEN)
    
    # Vérifications pour les utilisateurs connectés
    elif user_role == 'free' and question_count > 6:
        return Response({
            'error': 'Limite atteinte. Les comptes gratuits sont limités à 6 questions maximum.',
            'details': 'Passez à Premium pour créer des quiz avec un nombre illimité de questions.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Vérifier les limites de quiz par jour pour les utilisateurs connectés
    if user and not user.can_create_quiz_today():
        if user_role == 'free':
            return Response({
                'error': 'Limite de quiz quotidienne atteinte. Vous avez utilisé votre quota gratuit du jour.',
                'details': 'Passez à Premium pour un accès illimité et débloquer toutes les fonctionnalités.'
            }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Limite de quiz quotidienne atteinte. Passez à Premium pour un accès illimité.'}, status=status.HTTP_403_FORBIDDEN)
    
    # Sauvegarder le fichier
    file_extension = os.path.splitext(file.name)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Pour les guests, créer un utilisateur temporaire ou utiliser None
    document_user = user if user else None
    
    document = Document.objects.create(
        user=document_user,
        guest_session=guest_session if user_role == 'guest' else None,
        title=title,
        file=file,
        file_type=file_extension
    )
    
    # Générer des questions avec l'IA
    try:
        create_ai_questions(document, question_count, difficulty, question_types, education_level, instructions)
    except Exception as e:
        # Supprimer le document en cas d'erreur
        document.delete()
        logger.error(f"❌ Erreur lors de la génération des questions: {e}")
        return Response({
            'error': str(e),
            'details': 'Erreur lors de la génération des questions. Veuillez réessayer.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Créer automatiquement une leçon
    lesson = Lesson.objects.create(
        user=document_user,
        document=document,
        title=title,
        difficulty='medium'
    )
    
    # Incrémenter le compteur de quiz pour les utilisateurs connectés
    if user:
        user.increment_quiz_count()
    else:
        # Incrémenter l'utilisation pour les invités
        from .guest_utils import increment_guest_usage
        increment_guest_usage(guest_session)
    
    # Associer les questions du document à la leçon
    questions = Question.objects.filter(document=document)
    lesson.total_questions = questions.count()
    lesson.save()
    
    # Mettre à jour les questions pour les associer à la leçon
    questions.update(lesson=lesson)
    
    # Préparer la réponse
    response_data = {
        'document_id': document.id,
        'lesson_id': lesson.id,
        'title': document.title,
        'questions_count': questions.count(),
        'message': 'Document uploadé et questions générées avec succès'
    }
    
    # Ajouter l'ID de session pour les invités
    if user_role == 'guest':
        response_data['session_id'] = guest_session.session_id
        response_data['remaining_uses'] = 0  # Plus d'utilisations disponibles
        response_data['message'] = 'Document uploadé avec succès ! Inscrivez-vous pour sauvegarder vos résultats et créer plus de quiz.'
    
    return Response(response_data, status=status.HTTP_201_CREATED)

def create_ai_questions(document, question_count=5, difficulty='medium', question_types='["qcm"]', education_level='', instructions=''):
    """Crée des questions avec l'IA OpenAI"""
    
    try:
        # Vérifier que le fichier existe
        if not document.file or not os.path.exists(document.file.path):
            raise Exception(f"Fichier non trouvé: {document.file.path if document.file else 'Aucun fichier'}")
        
        # Utiliser le service OpenAI avec le chemin du fichier
        ai_service = OpenAIService()
        questions_data = ai_service.generate_questions_from_document(
            file_path=document.file.path,
            document_title=document.title,
            question_count=question_count,
            difficulty=difficulty,
            education_level=education_level,
            instructions=instructions
        )
        
        # Créer les questions et réponses
        for q_data in questions_data:
            question = Question.objects.create(
                document=document,
                question_text=q_data['question_text'],
                question_type='qcm',
                difficulty=q_data['difficulty']
            )
            
            # Créer les réponses
            for answer_data in q_data['answers']:
                Answer.objects.create(
                    question=question,
                    answer_text=answer_data['text'],
                    is_correct=answer_data['is_correct']
                )
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de la génération IA: {e}")
        raise Exception(f"Impossible de générer les questions avec l'IA: {e}")

def create_mock_questions(document, question_count=5, difficulty='medium', question_types='["qcm"]'):
    """Crée des questions mockées pour le document - Fallback"""
    
    # Simuler un délai de traitement IA
    import time
    import json
    time.sleep(1)  # Simulation du temps de traitement
    
    # Parser les types de questions
    try:
        types_list = json.loads(question_types)
    except:
        types_list = ['qcm']
    
    # Questions générées "par l'IA" basées sur le type de fichier
    file_type = document.file_type.lower()
    
    # Templates de questions selon le type de fichier
    if 'pdf' in file_type or 'doc' in file_type:
        # Questions pour documents textuels
        question_templates = [
            {
                'text': f"Quel est le sujet principal abordé dans le document '{document.title}' ?",
                'answers': [
                    {'text': 'Les concepts fondamentaux', 'correct': True},
                    {'text': 'Les détails techniques', 'correct': False},
                    {'text': 'Les exemples pratiques', 'correct': False},
                    {'text': 'Les conclusions', 'correct': False}
                ]
            },
            {
                'text': "Quelle méthode est recommandée dans ce document ?",
                'answers': [
                    {'text': 'La méthode traditionnelle', 'correct': False},
                    {'text': 'La méthode progressive', 'correct': True},
                    {'text': 'La méthode rapide', 'correct': False},
                    {'text': 'La méthode alternative', 'correct': False}
                ]
            },
            {
                'text': "Selon le document, quel est le point le plus important à retenir ?",
                'answers': [
                    {'text': 'Les détails techniques', 'correct': False},
                    {'text': "L'approche globale", 'correct': True},
                    {'text': 'Les exemples concrets', 'correct': False},
                    {'text': 'Les limitations', 'correct': False}
                ]
            },
            {
                'text': "Quelle est la structure principale de ce document ?",
                'answers': [
                    {'text': 'Introduction, développement, conclusion', 'correct': True},
                    {'text': 'Problème, solution, évaluation', 'correct': False},
                    {'text': 'Thèse, arguments, réfutation', 'correct': False},
                    {'text': 'Contexte, analyse, recommandations', 'correct': False}
                ]
            },
            {
                'text': "Quel est l'objectif principal de ce document ?",
                'answers': [
                    {'text': 'Informer le lecteur', 'correct': True},
                    {'text': 'Persuader le lecteur', 'correct': False},
                    {'text': 'Divertir le lecteur', 'correct': False},
                    {'text': 'Critiquer une théorie', 'correct': False}
                ]
            }
        ]
    else:
        # Questions pour images/photos
        question_templates = [
            {
                'text': f"Que représente l'image '{document.title}' ?",
                'answers': [
                    {'text': 'Un diagramme explicatif', 'correct': True},
                    {'text': 'Une photographie', 'correct': False},
                    {'text': 'Un graphique', 'correct': False},
                    {'text': 'Un schéma technique', 'correct': False}
                ]
            },
            {
                'text': "Quel élément est le plus visible dans cette image ?",
                'answers': [
                    {'text': 'Le texte principal', 'correct': True},
                    {'text': 'Les détails secondaires', 'correct': False},
                    {'text': "L'arrière-plan", 'correct': False},
                    {'text': 'Les annotations', 'correct': False}
                ]
            },
            {
                'text': "Quelle est la fonction principale de cette image ?",
                'answers': [
                    {'text': 'Illustrer un concept', 'correct': True},
                    {'text': 'Décorer le document', 'correct': False},
                    {'text': 'Montrer un exemple', 'correct': False},
                    {'text': 'Expliquer un processus', 'correct': False}
                ]
            },
            {
                'text': "Quel type de contenu cette image présente-t-elle ?",
                'answers': [
                    {'text': 'Du contenu éducatif', 'correct': True},
                    {'text': 'Du contenu publicitaire', 'correct': False},
                    {'text': 'Du contenu artistique', 'correct': False},
                    {'text': 'Du contenu technique', 'correct': False}
                ]
            },
            {
                'text': "Dans quel contexte cette image est-elle utilisée ?",
                'answers': [
                    {'text': 'Dans un contexte pédagogique', 'correct': True},
                    {'text': 'Dans un contexte commercial', 'correct': False},
                    {'text': 'Dans un contexte scientifique', 'correct': False},
                    {'text': 'Dans un contexte artistique', 'correct': False}
                ]
            }
        ]
    
    # Sélectionner le nombre de questions demandé
    selected_questions = question_templates[:question_count]
    
    # Créer les questions et réponses
    for q_data in selected_questions:
        question = Question.objects.create(
            document=document,
            question_text=q_data['text'],
            question_type='qcm',  # Seulement QCM
            difficulty=difficulty
        )
        
        # Ajouter les réponses pour les QCM
        for answer_data in q_data['answers']:
            Answer.objects.create(
                question=question,
                answer_text=answer_data['text'],
                is_correct=answer_data['correct']
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_documents(request):
    documents = Document.objects.filter(user=request.user).order_by('-created_at')
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_questions(request, document_id):
    try:
        document = Document.objects.get(id=document_id, user=request.user)
        questions = Question.objects.filter(document=document).order_by('created_at')
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
    except Document.DoesNotExist:
        return Response({'error': 'Document non trouvé'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lessons(request):
    """Récupère toutes les leçons de l'utilisateur"""
    lessons = Lesson.objects.filter(user=request.user).order_by('-last_accessed')
    serializer = LessonSerializer(lessons, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_lesson(request):
    """Crée une nouvelle leçon à partir d'un document"""
    try:
        document_id = request.data.get('document_id')
        document = Document.objects.get(id=document_id, user=request.user)
        
        # Créer la leçon
        lesson = Lesson.objects.create(
            user=request.user,
            document=document,
            title=request.data.get('title', document.title),
            difficulty=request.data.get('difficulty', 'medium')
        )
        
        # Associer les questions du document à la leçon
        questions = Question.objects.filter(document=document)
        lesson.total_questions = questions.count()
        lesson.save()
        
        # Mettre à jour les questions pour les associer à la leçon
        questions.update(lesson=lesson)
        
        serializer = LessonSerializer(lesson)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Document.DoesNotExist:
        return Response({'error': 'Document non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_lesson(request, lesson_id):
    """Récupère une leçon spécifique avec ses questions"""
    try:
        import random
        
        # Récupérer session_id pour les invités
        session_id = request.GET.get('session_id')
        
        if request.user.is_authenticated:
            # Utilisateur connecté
            lesson = Lesson.objects.get(id=lesson_id, user=request.user)
            
            # Vérifier les limites de tentatives pour les utilisateurs non premium
            if not request.user.is_premium:
                if not request.user.can_attempt_quiz_today():
                    return Response({
                        'error': 'Limite de tentatives quotidienne atteinte. Vous avez utilisé vos 2 tentatives gratuites du jour.',
                        'details': 'Passez à Premium pour un accès illimité et débloquer toutes les fonctionnalités.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Incrémenter le compteur de tentatives
                request.user.increment_attempt_count()
        else:
            # Invité - vérifier la session
            from .guest_utils import get_or_create_guest_session
            guest_session = get_or_create_guest_session(request, session_id)
            
            # Récupérer la leçon de l'invité (user=None)
            try:
                lesson = Lesson.objects.get(id=lesson_id, user=None)
            except Lesson.DoesNotExist:
                return Response({'error': 'Quiz non trouvé'}, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier que la leçon appartient à cette session invité
            # (on peut vérifier via le document associé)
            if lesson.document.user is not None or lesson.document.guest_session != guest_session:
                return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
        
        questions = Question.objects.filter(lesson=lesson).order_by('created_at')
        
        lesson_serializer = LessonSerializer(lesson)
        questions_serializer = QuestionSerializer(questions, many=True)
        
        # Mélanger l'ordre des réponses pour chaque question
        questions_data = questions_serializer.data
        for question in questions_data:
            if question['answers']:
                # Mélanger l'ordre des réponses
                random.shuffle(question['answers'])
        
        response_data = {
            'lesson': lesson_serializer.data,
            'questions': questions_data
        }
        
        # Ajouter session_id pour les invités
        if not request.user.is_authenticated:
            response_data['session_id'] = guest_session.session_id
        
        return Response(response_data)
    except Lesson.DoesNotExist:
        return Response({'error': 'Leçon non trouvée'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_answer(request, lesson_id):
    """Soumet une réponse à une question"""
    try:
        # Récupérer session_id pour les invités
        session_id = request.data.get('session_id')
        
        if request.user.is_authenticated:
            # Utilisateur connecté
            lesson = Lesson.objects.get(id=lesson_id, user=request.user)
            user = request.user
            guest_session = None
        else:
            # Invité - vérifier la session
            from .guest_utils import get_or_create_guest_session
            guest_session = get_or_create_guest_session(request, session_id)
            user = None
            
            # Récupérer la leçon de l'invité (user=None)
            lesson = Lesson.objects.get(id=lesson_id, user=None)
            
            # Vérifier que la leçon appartient à cette session invité
            if lesson.document.user is not None:
                return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
        
        question_id = request.data.get('question_id')
        question = Question.objects.get(id=question_id, lesson=lesson)
        
        # Supprimer les anciennes réponses pour permettre la révision
        if user:
            UserAnswer.objects.filter(
                user=user, 
                question=question, 
                lesson=lesson
            ).delete()
        else:
            UserAnswer.objects.filter(
                guest_session=guest_session, 
                question=question, 
                lesson=lesson
            ).delete()
        
        # Traiter la réponse
        is_correct = False
        selected_answer = None
        open_answer = None
        
        if question.question_type == 'qcm':
            selected_answer_id = request.data.get('selected_answer_id')
            selected_answer = Answer.objects.get(id=selected_answer_id, question=question)
            is_correct = selected_answer.is_correct
        else:  # question ouverte
            open_answer = request.data.get('open_answer', '')
            # Pour l'instant, on considère toutes les réponses ouvertes comme correctes
            # Dans une vraie app, il faudrait une logique d'évaluation
            is_correct = True
        
        # Créer la réponse utilisateur
        user_answer = UserAnswer.objects.create(
            user=user,
            guest_session=guest_session,
            question=question,
            lesson=lesson,
            selected_answer=selected_answer,
            open_answer=open_answer,
            is_correct=is_correct
        )
        
        # Recalculer les statistiques de la leçon
        if user:
            # Utilisateur connecté
            answered_questions = UserAnswer.objects.filter(user=user, lesson=lesson).values('question').distinct()
            correct_answers = UserAnswer.objects.filter(user=user, lesson=lesson, is_correct=True).values('question').distinct().count()
        else:
            # Invité
            answered_questions = UserAnswer.objects.filter(guest_session=guest_session, lesson=lesson).values('question').distinct()
            correct_answers = UserAnswer.objects.filter(guest_session=guest_session, lesson=lesson, is_correct=True).values('question').distinct().count()
        
        lesson.completed_questions = answered_questions.count()
        new_score = int((correct_answers / lesson.total_questions) * 100) if lesson.total_questions > 0 else 0
        
        # Marquer comme terminé si toutes les questions sont répondues
        if lesson.completed_questions >= lesson.total_questions:
            lesson.status = 'termine'
            # Mettre à jour les scores et statistiques SEULEMENT quand le quiz est terminé
            lesson.update_scores(new_score)
            
            # Créer un enregistrement de tentative (seulement pour les utilisateurs connectés)
            if user:
                attempt_number = lesson.total_attempts
                LessonAttempt.objects.create(
                    lesson=lesson,
                    attempt_number=attempt_number,
                    score=new_score
                )
        else:
            lesson.status = 'en_cours'
            # Mettre à jour seulement le score actuel, pas les statistiques
            lesson.score = new_score
        
        lesson.save()
        
        response_data = {
            'is_correct': is_correct,
            'lesson_progress': lesson.progress,
            'lesson_score': lesson.score
        }
        
        # Ajouter session_id pour les invités
        if not request.user.is_authenticated:
            response_data['session_id'] = guest_session.session_id
        
        return Response(response_data)
        
    except (Lesson.DoesNotExist, Question.DoesNotExist, Answer.DoesNotExist):
        return Response({'error': 'Ressource non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_guest_quiz_results(request, lesson_id):
    """Récupère les résultats d'un quiz invité (sans les afficher)"""
    try:
        session_id = request.GET.get('session_id')
        
        if request.user.is_authenticated:
            return Response({'error': 'Cette fonction est réservée aux invités'}, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier la session invité
        from .guest_utils import get_or_create_guest_session
        guest_session = get_or_create_guest_session(request, session_id)
        
        # Récupérer la leçon de l'invité
        lesson = Lesson.objects.get(id=lesson_id, user=None)
        
        # Vérifier que la leçon appartient à cette session invité
        if lesson.document.user is not None:
            return Response({'error': 'Accès refusé'}, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer les réponses de l'invité
        user_answers = UserAnswer.objects.filter(guest_session=guest_session, lesson=lesson)
        
        # Calculer le score
        correct_answers = user_answers.filter(is_correct=True).count()
        total_questions = lesson.total_questions
        score_percentage = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
        
        # Vérifier si le quiz est terminé
        is_completed = lesson.status == 'termine'
        
        response_data = {
            'lesson_id': lesson.id,
            'lesson_title': lesson.title,
            'is_completed': is_completed,
            'total_questions': total_questions,
            'answered_questions': user_answers.count(),
            'correct_answers': correct_answers,
            'score_percentage': score_percentage,
            'session_id': guest_session.session_id,
            'can_see_results': False,  # Les invités ne peuvent pas voir les résultats
            'message': 'Quiz terminé ! Inscrivez-vous pour voir vos résultats détaillés et sauvegarder vos progrès.'
        }
        
        return Response(response_data)
        
    except Lesson.DoesNotExist:
        return Response({'error': 'Leçon non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_guest_data(request):
    """Transfère les données d'une session invité vers le compte utilisateur"""
    try:
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response({'error': 'Session ID requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la session invité
        try:
            guest_session = GuestSession.objects.get(session_id=session_id)
        except GuestSession.DoesNotExist:
            return Response({'error': 'Session invité non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier que la session n'a pas déjà été transférée
        if guest_session.transferred_to_user:
            return Response({'error': 'Cette session a déjà été transférée'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer les documents avant le transfert
        documents_before_transfer = list(Document.objects.filter(guest_session=guest_session).values_list('id', flat=True))
        
        # Transférer les données
        guest_session.transfer_to_user(request.user)
        
        # Récupérer les leçons transférées via les documents
        transferred_lessons = Lesson.objects.filter(user=request.user, document_id__in=documents_before_transfer)
        
        response_data = {
            'success': True,
            'message': 'Vos données ont été transférées avec succès !',
            'transferred_lessons': [
                {
                    'id': lesson.id,
                    'title': lesson.title,
                    'score': lesson.score,
                    'status': lesson.status
                }
                for lesson in transferred_lessons
            ]
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_lesson(request, lesson_id):
    """Réinitialise une leçon pour permettre de la refaire"""
    try:
        lesson = Lesson.objects.get(id=lesson_id, user=request.user)
        
        # Supprimer toutes les réponses de l'utilisateur pour cette leçon
        UserAnswer.objects.filter(user=request.user, lesson=lesson).delete()
        
        # Réinitialiser seulement les champs nécessaires pour relancer le quiz
        lesson.completed_questions = 0
        lesson.score = 0
        lesson.status = 'en_cours'
        # NE PAS réinitialiser last_score, total_attempts, average_score
        lesson.save()
        
        return Response({'message': 'Leçon réinitialisée avec succès'})
        
    except Lesson.DoesNotExist:
        return Response({'error': 'Leçon non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lesson_stats(request):
    """Récupère les statistiques de l'utilisateur"""
    lessons = Lesson.objects.filter(user=request.user)
    
    total_lessons = lessons.count()
    completed_lessons = lessons.filter(status='termine').count()
    
    # Calculer le score moyen
    scores = [lesson.score for lesson in lessons if lesson.score > 0]
    average_score = sum(scores) / len(scores) if scores else 0
    
    # Pour l'instant, on simule le temps d'étude
    # Dans une vraie app, il faudrait tracker le temps réel
    total_study_time = completed_lessons * 30  # 30 minutes par leçon terminée
    
    stats = {
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'average_score': round(average_score, 1),
        'total_study_time': total_study_time
    }
    
    serializer = LessonStatsSerializer(stats)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lesson_attempts(request, lesson_id):
    """Récupère l'historique des tentatives pour une leçon"""
    try:
        lesson = Lesson.objects.get(id=lesson_id, user=request.user)
        attempts = LessonAttempt.objects.filter(lesson=lesson).order_by('attempt_number')
        
        serializer = LessonAttemptSerializer(attempts, many=True)
        return Response(serializer.data)
    except Lesson.DoesNotExist:
        return Response({'error': 'Leçon non trouvée'}, status=status.HTTP_404_NOT_FOUND)
