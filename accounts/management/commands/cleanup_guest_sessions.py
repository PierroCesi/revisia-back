"""
Commande Django pour nettoyer les sessions invités expirées
Usage: python manage.py cleanup_guest_sessions
"""
from django.core.management.base import BaseCommand
from accounts.guest_utils import cleanup_expired_guest_sessions, get_guest_stats

class Command(BaseCommand):
    help = 'Nettoie les sessions invités expirées et leurs documents associés'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait supprimé sans effectuer la suppression',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Affiche les statistiques des sessions invités',
        )
        parser.add_argument(
            '--unblock-ip',
            type=str,
            help='Débloquer une adresse IP spécifique en supprimant ses sessions invités',
        )

    def handle(self, *args, **options):
        if options['stats']:
            self.show_stats()
            return

        if options['unblock_ip']:
            self.unblock_ip(options['unblock_ip'])
            return

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('Mode dry-run activé - aucune suppression ne sera effectuée')
            )
            # TODO: Implémenter le mode dry-run
            return

        self.stdout.write('Nettoyage des sessions invités expirées...')
        
        try:
            cleaned_count = cleanup_expired_guest_sessions()
            
            if cleaned_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {cleaned_count} sessions expirées nettoyées avec succès')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ Aucune session expirée à nettoyer')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur lors du nettoyage: {e}')
            )

    def show_stats(self):
        """Affiche les statistiques des sessions invités"""
        try:
            stats = get_guest_stats()
            
            self.stdout.write('\n📊 Statistiques des sessions invités:')
            self.stdout.write(f'  • Sessions totales: {stats.get("total_sessions", 0)}')
            self.stdout.write(f'  • Sessions actives (24h): {stats.get("active_sessions", 0)}')
            self.stdout.write(f'  • Sessions bloquées: {stats.get("blocked_sessions", 0)}')
            self.stdout.write(f'  • Sessions expirées: {stats.get("expired_sessions", 0)}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur lors du calcul des statistiques: {e}')
            )

    def unblock_ip(self, ip_address):
        """Débloque une adresse IP en supprimant ses sessions invités"""
        try:
            from accounts.models import GuestSession
            from django.core.cache import cache
            
            # Supprimer les sessions invités pour cette IP
            sessions = GuestSession.objects.filter(ip_address=ip_address)
            count = sessions.count()
            
            if count > 0:
                # Supprimer les documents associés
                for session in sessions:
                    from accounts.models import Document, Lesson, UserAnswer
                    Document.objects.filter(guest_session=session).delete()
                    Lesson.objects.filter(user=None, document__guest_session=session).delete()
                    UserAnswer.objects.filter(guest_session=session).delete()
                
                # Supprimer les sessions
                sessions.delete()
                
                # Nettoyer le cache de rate limiting
                cache_key = f'rate_limit:{ip_address}'
                cache.delete(cache_key)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ IP {ip_address} débloquée - {count} sessions supprimées')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Aucune session trouvée pour l\'IP {ip_address}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur lors du déblocage de l\'IP {ip_address}: {e}')
            )
