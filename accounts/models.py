from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    education_level = models.CharField(max_length=100, blank=True, null=True, help_text="Niveau d'éducation de l'utilisateur")
    
    # Champs pour le système de rôles
    is_premium = models.BooleanField(default=False, help_text="Utilisateur premium")
    premium_expires_at = models.DateTimeField(null=True, blank=True, help_text="Expiration du statut premium")
    quiz_count_today = models.IntegerField(default=0, help_text="Nombre de quiz créés aujourd'hui")
    last_quiz_date = models.DateField(null=True, blank=True, help_text="Date du dernier quiz créé")
    attempts_count_today = models.IntegerField(default=0, help_text="Nombre de tentatives de quiz aujourd'hui")
    last_attempt_date = models.DateField(null=True, blank=True, help_text="Date de la dernière tentative")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    def get_user_role(self):
        """Retourne le rôle de l'utilisateur"""
        if self.is_premium:
            return 'premium'
        elif self.is_authenticated:
            return 'free'
        else:
            return 'guest'
    
    def can_create_quiz_today(self):
        """Vérifie si l'utilisateur peut créer un quiz aujourd'hui"""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Reset du compteur si ce n'est pas le même jour
        if self.last_quiz_date != today:
            self.quiz_count_today = 0
            self.last_quiz_date = today
            self.save(update_fields=['quiz_count_today', 'last_quiz_date'])
        
        if self.is_premium:
            return True
        else:
            return self.quiz_count_today < 1
    
    def increment_quiz_count(self):
        """Incrémente le compteur de quiz du jour"""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        if self.last_quiz_date != today:
            self.quiz_count_today = 1
            self.last_quiz_date = today
        else:
            self.quiz_count_today += 1
        
        self.save(update_fields=['quiz_count_today', 'last_quiz_date'])
    
    def can_attempt_quiz_today(self):
        """Vérifie si l'utilisateur peut faire une tentative de quiz aujourd'hui"""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Reset du compteur si ce n'est pas le même jour
        if self.last_attempt_date != today:
            self.attempts_count_today = 0
            self.last_attempt_date = today
            self.save(update_fields=['attempts_count_today', 'last_attempt_date'])
        
        if self.is_premium:
            return True
        else:
            return self.attempts_count_today < 2
    
    def increment_attempt_count(self):
        """Incrémente le compteur de tentatives du jour"""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Reset du compteur si ce n'est pas le même jour
        if self.last_attempt_date != today:
            self.attempts_count_today = 1
            self.last_attempt_date = today
        else:
            self.attempts_count_today += 1
        
        self.save(update_fields=['attempts_count_today', 'last_attempt_date'])

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', null=True, blank=True, help_text="Utilisateur propriétaire du document (null pour les invités)")
    guest_session = models.ForeignKey('GuestSession', on_delete=models.CASCADE, null=True, blank=True, help_text="Session invité (pour les documents d'invités)")
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons', null=True, blank=True, help_text="Utilisateur propriétaire de la leçon (null pour les invités)")
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
        if self.user:
            return f"{self.title} - {self.user.username}"
        else:
            return f"{self.title} - Invité"

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, help_text="Utilisateur (null pour les invités)")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_answers')
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    open_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    # Champs pour les invités
    guest_session = models.ForeignKey('GuestSession', on_delete=models.CASCADE, null=True, blank=True, help_text="Session invité (pour les utilisateurs non connectés)")
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.question.question_text[:30]}"
        else:
            return f"Invité - {self.question.question_text[:30]}"

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

class GuestSession(models.Model):
    """Sessions temporaires pour les utilisateurs invités"""
    ip_address = models.GenericIPAddressField(help_text="Adresse IP de l'invité")
    session_id = models.CharField(max_length=100, unique=True, help_text="ID de session unique")
    documents_created = models.PositiveIntegerField(default=0, help_text="Nombre de documents créés")
    last_activity = models.DateTimeField(auto_now=True, help_text="Dernière activité")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date de création de la session")
    is_blocked = models.BooleanField(default=False, help_text="Session bloquée (limite atteinte)")
    
    # Champs pour le transfert vers compte utilisateur
    transferred_to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Utilisateur vers lequel la session a été transférée")
    transferred_at = models.DateTimeField(null=True, blank=True, help_text="Date de transfert vers compte utilisateur")
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['transferred_to_user']),
        ]
    
    def can_create_document(self):
        """Vérifie si l'invité peut créer un document"""
        return not self.is_blocked and self.documents_created < 1
    
    def increment_document_count(self):
        """Incrémente le compteur de documents et bloque si nécessaire"""
        self.documents_created += 1
        if self.documents_created >= 1:
            self.is_blocked = True
        self.save()
    
    def is_expired(self, hours=24):
        """Vérifie si la session a expiré (24h par défaut)"""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.created_at > timedelta(hours=hours)
    
    def transfer_to_user(self, user):
        """Transfère la session et ses données vers un utilisateur"""
        from django.utils import timezone
        
        # Transférer les réponses
        UserAnswer.objects.filter(guest_session=self).update(user=user, guest_session=None)
        
        # Transférer les documents
        documents = Document.objects.filter(guest_session=self)
        document_ids = list(documents.values_list('id', flat=True))
        documents.update(user=user, guest_session=None)
        
        # Transférer les leçons associées à ces documents
        Lesson.objects.filter(user=None, document_id__in=document_ids).update(user=user)
        
        # Marquer la session comme transférée
        self.transferred_to_user = user
        self.transferred_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Guest Session {self.session_id[:8]}... - {self.ip_address} ({self.documents_created} docs)"
