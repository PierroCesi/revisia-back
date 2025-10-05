from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Document, Question, Answer, Lesson, UserAnswer, LessonAttempt

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'education_level', 'password', 'password_confirm')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Identifiants invalides.')
            if not user.is_active:
                raise serializers.ValidationError('Compte désactivé.')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Email et mot de passe requis.')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'education_level', 'created_at')

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'title', 'file_type', 'created_at')

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('id', 'answer_text', 'is_correct')

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'difficulty', 'answers', 'created_at')

class LessonSerializer(serializers.ModelSerializer):
    progress = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = Lesson
        fields = (
            'id', 'title', 'status', 'difficulty', 'total_questions', 
            'completed_questions', 'score', 'last_score', 'total_attempts', 
            'average_score', 'progress', 'is_completed',
            'last_accessed', 'created_at', 'document_title'
        )

class UserAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = (
            'id', 'question', 'question_text', 'selected_answer', 
            'open_answer', 'is_correct', 'answered_at'
        )

class LessonAttemptSerializer(serializers.ModelSerializer):
    user_answers = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonAttempt
        fields = ('attempt_number', 'score', 'completed_at', 'user_answers')
    
    def get_user_answers(self, obj):
        """Récupère les réponses de l'utilisateur pour cette tentative"""
        # Récupérer toutes les questions de la leçon
        questions = Question.objects.filter(document=obj.lesson.document).order_by('id')
        
        # Pour cette tentative, on récupère les réponses les plus récentes
        # car le système actuel ne stocke pas attempt_number dans UserAnswer
        # On utilise la date de création de la tentative comme référence
        answers_data = []
        
        for question in questions:
            # Récupérer la réponse de l'utilisateur pour cette leçon
            # On prend la réponse la plus récente pour cette question
            try:
                user_answer = UserAnswer.objects.filter(
                    question=question,
                    lesson=obj.lesson
                ).order_by('-answered_at').first()
                
                if user_answer:
                    # Récupérer toutes les réponses possibles pour cette question
                    all_answers = Answer.objects.filter(question=question).order_by('id')
                    
                    answers_data.append({
                        'question_id': question.id,
                        'question_text': question.question_text,
                        'difficulty': question.difficulty,
                        'user_answer_id': user_answer.selected_answer_id,
                        'user_answer_text': user_answer.selected_answer.answer_text if user_answer.selected_answer else None,
                        'is_correct': user_answer.is_correct,
                        'all_answers': [
                            {
                                'id': answer.id,
                                'text': answer.answer_text,
                                'is_correct': answer.is_correct
                            }
                            for answer in all_answers
                        ]
                    })
                else:
                    # Si pas de réponse trouvée, marquer comme non répondu
                    all_answers = Answer.objects.filter(question=question).order_by('id')
                    answers_data.append({
                        'question_id': question.id,
                        'question_text': question.question_text,
                        'difficulty': question.difficulty,
                        'user_answer_id': None,
                        'user_answer_text': None,
                        'is_correct': False,
                        'all_answers': [
                            {
                                'id': answer.id,
                                'text': answer.answer_text,
                                'is_correct': answer.is_correct
                            }
                            for answer in all_answers
                        ]
                    })
            except Exception as e:
                # En cas d'erreur, créer une entrée vide
                all_answers = Answer.objects.filter(question=question).order_by('id')
                answers_data.append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'difficulty': question.difficulty,
                    'user_answer_id': None,
                    'user_answer_text': None,
                    'is_correct': False,
                    'all_answers': [
                        {
                            'id': answer.id,
                            'text': answer.answer_text,
                            'is_correct': answer.is_correct
                        }
                        for answer in all_answers
                    ]
                })
        
        return answers_data

class LessonStatsSerializer(serializers.Serializer):
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    average_score = serializers.FloatField()
    total_study_time = serializers.IntegerField()  # en minutes
