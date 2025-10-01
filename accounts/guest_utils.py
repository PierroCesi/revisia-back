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
    Récupère ou crée une session invité permanente (une seule par IP)
    """
    ip_address = get_client_ip(request)
    
    # Essayer de récupérer une session existante pour cette IP
    try:
        session = GuestSession.objects.get(ip_address=ip_address)
        logger.info(f"Session invité existante trouvée pour IP {ip_address}: {session.session_id}")
        return session
    except GuestSession.DoesNotExist:
        # Aucune session existante pour cette IP
        pass
    
    # Si un session_id est fourni, essayer de le récupérer (pour compatibilité)
    if session_id:
        try:
            session = GuestSession.objects.get(session_id=session_id)
            logger.info(f"Session invité trouvée par session_id: {session_id}")
            return session
        except GuestSession.DoesNotExist:
            logger.warning(f"Session invité introuvable: {session_id}")
    
    # Créer une nouvelle session permanente
    return create_new_guest_session(ip_address)

def create_new_guest_session(ip_address):
    """Crée une nouvelle session invité permanente"""
    session_id = str(uuid.uuid4())
    session = GuestSession.objects.create(
        ip_address=ip_address,
        session_id=session_id
    )
    logger.info(f"Nouvelle session invité permanente créée: {session_id} pour IP {ip_address}")
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
    """Nettoie les sessions invités expirées et leurs documents (désactivé - sessions permanentes)"""
    # Sessions permanentes - pas de nettoyage automatique
    logger.info("Nettoyage des sessions invités désactivé - sessions permanentes")
    return 0

def get_guest_stats():
    """Retourne les statistiques des invités"""
    try:
        total_sessions = GuestSession.objects.count()
        blocked_sessions = GuestSession.objects.filter(is_blocked=True).count()
        active_sessions = total_sessions - blocked_sessions
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'blocked_sessions': blocked_sessions,
            'expired_sessions': 0  # Sessions permanentes
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
