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
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'created_at')

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
    class Meta:
        model = LessonAttempt
        fields = ('attempt_number', 'score', 'completed_at')

class LessonStatsSerializer(serializers.Serializer):
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    average_score = serializers.FloatField()
    total_study_time = serializers.IntegerField()  # en minutes
