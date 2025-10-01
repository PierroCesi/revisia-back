"""
Utilitaires pour la gestion des sessions invités
"""
import uuid
import logging
from django.utils import timezone
from django.core.cache import cache
from .models import GuestSession, Document

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Récupère l'adresse IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_or_create_guest_session(request, session_id=None):
    """
    Récupère ou crée une session invité
    """
    ip_address = get_client_ip(request)
    
    # Si un session_id est fourni, essayer de le récupérer
    if session_id:
        try:
            session = GuestSession.objects.get(session_id=session_id, ip_address=ip_address)
            # Vérifier si la session n'a pas expiré
            if session.is_expired():
                logger.info(f"Session invité expirée: {session_id}")
                session.delete()
                return create_new_guest_session(ip_address)
            return session
        except GuestSession.DoesNotExist:
            logger.warning(f"Session invité introuvable: {session_id}")
    
    # Créer une nouvelle session
    return create_new_guest_session(ip_address)

def create_new_guest_session(ip_address):
    """Crée une nouvelle session invité"""
    session_id = str(uuid.uuid4())
    session = GuestSession.objects.create(
        ip_address=ip_address,
        session_id=session_id
    )
    logger.info(f"Nouvelle session invité créée: {session_id} pour IP {ip_address}")
    return session

def check_guest_limits(request, session_id=None):
    """
    Vérifie les limites pour un invité
    Retourne (is_allowed, session, error_message)
    """
    try:
        session = get_or_create_guest_session(request, session_id)
        
        # Vérifier si la session peut créer un document
        if not session.can_create_document():
            if session.is_blocked:
                return False, session, {
                    'error': 'Limite d\'utilisation atteinte',
                    'details': 'Vous avez déjà utilisé votre quota gratuit. Inscrivez-vous pour créer plus de quiz et sauvegarder vos résultats.',
                    'action': 'signup_required'
                }
            else:
                return False, session, {
                    'error': 'Session expirée',
                    'details': 'Votre session a expiré. Veuillez rafraîchir la page.',
                    'action': 'refresh_required'
                }
        
        return True, session, None
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des limites invité: {e}")
        return False, None, {
            'error': 'Erreur de session',
            'details': 'Une erreur est survenue. Veuillez réessayer.',
            'action': 'retry_required'
        }

def increment_guest_usage(session):
    """Incrémente l'utilisation d'un invité"""
    try:
        session.increment_document_count()
        logger.info(f"Utilisation invité incrémentée: {session.session_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'incrémentation: {e}")
        return False

def cleanup_expired_guest_sessions():
    """Nettoie les sessions invités expirées et leurs documents"""
    try:
        # Récupérer les sessions expirées
        expired_sessions = GuestSession.objects.filter(
            created_at__lt=timezone.now() - timezone.timedelta(hours=24)
        )
        
        count = 0
        for session in expired_sessions:
            # Supprimer les documents associés (user=None)
            documents = Document.objects.filter(user=None)
            document_count = documents.count()
            documents.delete()
            
            # Supprimer la session
            session.delete()
            count += 1
            
            logger.info(f"Session expirée nettoyée: {session.session_id} ({document_count} documents supprimés)")
        
        logger.info(f"Nettoyage terminé: {count} sessions expirées supprimées")
        return count
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des sessions: {e}")
        return 0

def get_guest_stats():
    """Retourne les statistiques des invités"""
    try:
        total_sessions = GuestSession.objects.count()
        active_sessions = GuestSession.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        blocked_sessions = GuestSession.objects.filter(is_blocked=True).count()
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'blocked_sessions': blocked_sessions,
            'expired_sessions': total_sessions - active_sessions
        }
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {e}")
        return {}

def rate_limit_check(request, max_requests=5, window_minutes=60):
    """
    Vérifie le rate limiting par IP
    Retourne (is_allowed, remaining_requests)
    """
    ip_address = get_client_ip(request)
    cache_key = f"rate_limit:{ip_address}"
    
    # Récupérer le nombre de requêtes actuelles
    current_requests = cache.get(cache_key, 0)
    
    if current_requests >= max_requests:
        return False, 0
    
    # Incrémenter le compteur
    cache.set(cache_key, current_requests + 1, window_minutes * 60)
    
    return True, max_requests - current_requests - 1
