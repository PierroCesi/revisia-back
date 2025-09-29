from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer, 
    DocumentSerializer, QuestionSerializer, LessonSerializer, 
    UserAnswerSerializer, LessonStatsSerializer, LessonAttemptSerializer
)
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
    
    # Sauvegarder le fichier
    file_extension = os.path.splitext(file.name)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    document = Document.objects.create(
        user=request.user,
        title=title,
        file=file,
        file_type=file_extension
    )
    
    # Générer des questions mockées avec les paramètres
    create_ai_questions(document, question_count, difficulty, question_types, education_level)
    
    # Créer automatiquement une leçon
    lesson = Lesson.objects.create(
        user=request.user,
        document=document,
        title=title,
        difficulty='medium'
    )
    
    # Associer les questions du document à la leçon
    questions = Question.objects.filter(document=document)
    lesson.total_questions = questions.count()
    lesson.save()
    
    # Mettre à jour les questions pour les associer à la leçon
    questions.update(lesson=lesson)
    
    serializer = DocumentSerializer(document)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

def create_ai_questions(document, question_count=5, difficulty='medium', question_types='["qcm"]', education_level=''):
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
            education_level=education_level
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
@permission_classes([IsAuthenticated])
def get_lesson(request, lesson_id):
    """Récupère une leçon spécifique avec ses questions"""
    try:
        import random
        
        lesson = Lesson.objects.get(id=lesson_id, user=request.user)
        questions = Question.objects.filter(lesson=lesson).order_by('created_at')
        
        lesson_serializer = LessonSerializer(lesson)
        questions_serializer = QuestionSerializer(questions, many=True)
        
        # Mélanger l'ordre des réponses pour chaque question
        questions_data = questions_serializer.data
        for question in questions_data:
            if question['answers']:
                # Mélanger l'ordre des réponses
                random.shuffle(question['answers'])
        
        return Response({
            'lesson': lesson_serializer.data,
            'questions': questions_data
        })
    except Lesson.DoesNotExist:
        return Response({'error': 'Leçon non trouvée'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request, lesson_id):
    """Soumet une réponse à une question"""
    try:
        lesson = Lesson.objects.get(id=lesson_id, user=request.user)
        question_id = request.data.get('question_id')
        question = Question.objects.get(id=question_id, lesson=lesson)
        
        # Supprimer les anciennes réponses pour permettre la révision
        UserAnswer.objects.filter(
            user=request.user, 
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
            user=request.user,
            question=question,
            lesson=lesson,
            selected_answer=selected_answer,
            open_answer=open_answer,
            is_correct=is_correct
        )
        
        # Recalculer les statistiques de la leçon
        # Compter les questions uniques répondues (pas les réponses multiples)
        answered_questions = UserAnswer.objects.filter(user=request.user, lesson=lesson).values('question').distinct()
        lesson.completed_questions = answered_questions.count()
        
        # Calculer le score basé sur les bonnes réponses
        correct_answers = UserAnswer.objects.filter(user=request.user, lesson=lesson, is_correct=True).values('question').distinct().count()
        new_score = int((correct_answers / lesson.total_questions) * 100) if lesson.total_questions > 0 else 0
        
        # Marquer comme terminé si toutes les questions sont répondues
        if lesson.completed_questions >= lesson.total_questions:
            lesson.status = 'termine'
            # Mettre à jour les scores et statistiques SEULEMENT quand le quiz est terminé
            lesson.update_scores(new_score)
            
            # Créer un enregistrement de tentative
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
        
        return Response({
            'is_correct': is_correct,
            'lesson_progress': lesson.progress,
            'lesson_score': lesson.score
        })
        
    except (Lesson.DoesNotExist, Question.DoesNotExist, Answer.DoesNotExist):
        return Response({'error': 'Ressource non trouvée'}, status=status.HTTP_404_NOT_FOUND)
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
