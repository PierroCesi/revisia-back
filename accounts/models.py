from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    education_level = models.CharField(max_length=100, blank=True, null=True, help_text="Niveau d'éducation de l'utilisateur")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class Question(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='questions')
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=[
        ('qcm', 'QCM'),
        ('open', 'Question ouverte')
    ])
    difficulty = models.CharField(max_length=10, choices=[
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.question_text[:50] + "..."

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.answer_text[:30] + "..."

class Lesson(models.Model):
    STATUS_CHOICES = [
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('pause', 'En pause'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='en_cours')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    total_questions = models.PositiveIntegerField(default=0)
    completed_questions = models.PositiveIntegerField(default=0)
    score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    last_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_attempts = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def progress(self):
        if self.total_questions == 0:
            return 0
        return int((self.completed_questions / self.total_questions) * 100)
    
    @property
    def is_completed(self):
        return self.progress == 100
    
    def update_scores(self, new_score):
        """Met à jour les scores et statistiques après une tentative"""
        self.last_score = new_score
        self.total_attempts += 1
        
        # Calculer la nouvelle moyenne
        if self.total_attempts == 1:
            self.average_score = new_score
        else:
            # Moyenne pondérée : (ancienne_moyenne * (n-1) + nouveau_score) / n
            self.average_score = ((self.average_score * (self.total_attempts - 1)) + new_score) / self.total_attempts
        
        # Le score principal devient le dernier score
        self.score = new_score
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    open_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.question.question_text[:30]}"

class LessonAttempt(models.Model):
    """Historique des tentatives pour une leçon"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.PositiveIntegerField()
    score = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['attempt_number']
        unique_together = ['lesson', 'attempt_number']
    
    def __str__(self):
        return f"{self.lesson.title} - Tentative {self.attempt_number}: {self.score}%"
