# Système de Sécurité pour les Invités

## Vue d'ensemble

Ce système implémente des mécanismes de sécurité robustes pour limiter l'utilisation de l'application par les utilisateurs non connectés (invités), tout en permettant un test limité de l'outil.

## Fonctionnalités implémentées

### 1. 🔒 **Limitation "Une seule utilisation"**
- Chaque invité ne peut créer qu'**un seul document/quiz**
- Une fois la limite atteinte, l'invité est bloqué
- Message d'incitation à l'inscription

### 2. 🚦 **Rate Limiting par IP**
- Maximum **5 requêtes par heure** par adresse IP
- Protection contre le spam et les abus
- Utilisation du cache Django pour le suivi

### 3. ⏰ **Sessions temporaires (24h)**
- Chaque session invité expire après 24 heures
- Nettoyage automatique des sessions expirées
- Suivi de l'activité par session

### 4. 🧹 **Nettoyage automatique**
- Suppression automatique des documents invités expirés
- Commande de maintenance : `python manage.py cleanup_guest_sessions`
- Statistiques disponibles avec `--stats`

## Architecture technique

### Modèles

#### `GuestSession`
```python
class GuestSession(models.Model):
    ip_address = models.GenericIPAddressField()
    session_id = models.CharField(max_length=100, unique=True)
    documents_created = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_blocked = models.BooleanField(default=False)
```

#### `Document` (modifié)
```python
class Document(models.Model):
    user = models.ForeignKey(User, null=True, blank=True)  # Null pour les invités
    # ... autres champs
```

### Utilitaires (`guest_utils.py`)

#### Fonctions principales
- `get_or_create_guest_session()` : Gestion des sessions
- `check_guest_limits()` : Vérification des limites
- `rate_limit_check()` : Rate limiting par IP
- `cleanup_expired_guest_sessions()` : Nettoyage automatique

### Vues modifiées

#### `upload_document()`
- Vérification des limites invités
- Rate limiting par IP
- Gestion des sessions temporaires
- Messages d'erreur personnalisés

#### `user_role_info()`
- Informations de session pour les invités
- Suivi des utilisations restantes
- Statut de blocage

## Utilisation

### Pour les invités
1. **Première utilisation** : Création automatique d'une session
2. **Upload de document** : Limité à 5 questions maximum
3. **Après utilisation** : Session bloquée, incitation à l'inscription

### Pour les administrateurs

#### Nettoyage des sessions
```bash
# Nettoyage automatique
python manage.py cleanup_guest_sessions

# Statistiques
python manage.py cleanup_guest_sessions --stats

# Mode dry-run (à implémenter)
python manage.py cleanup_guest_sessions --dry-run
```

#### Surveillance
- Logs détaillés des actions invités
- Statistiques de conversion
- Suivi des abus potentiels

## Configuration

### Variables d'environnement
```env
# Rate limiting
GUEST_RATE_LIMIT=5          # Requêtes par heure
GUEST_RATE_WINDOW=60        # Fenêtre en minutes

# Sessions
GUEST_SESSION_DURATION=24   # Durée en heures
GUEST_MAX_DOCUMENTS=1       # Documents par session
```

### Cache
- Utilisation du cache Django pour le rate limiting
- Clé : `rate_limit:{ip_address}`
- TTL : 1 heure

## Sécurité

### Protection contre les abus
1. **Rate limiting** : Limite les requêtes par IP
2. **Session unique** : Une seule utilisation par session
3. **Expiration** : Nettoyage automatique après 24h
4. **Validation serveur** : Toutes les vérifications côté backend

### Limitations
- **IP partagée** : Plusieurs utilisateurs sur la même IP partagent les limites
- **Cache** : Le rate limiting dépend du cache Django
- **Sessions** : Les sessions sont stockées en base de données

## Monitoring

### Métriques à suivre
- Nombre de sessions invités créées
- Taux de conversion invité → utilisateur
- Nombre de sessions bloquées
- Requêtes bloquées par rate limiting

### Logs
```python
# Exemples de logs
logger.info(f"Nouvelle session invité créée: {session_id}")
logger.warning(f"Session invité introuvable: {session_id}")
logger.info(f"Session expirée nettoyée: {session_id}")
```

## Évolutions futures

### Améliorations possibles
1. **Géolocalisation** : Limites par pays/région
2. **Device fingerprinting** : Identification par appareil
3. **Machine learning** : Détection d'abus avancée
4. **API rate limiting** : Limites par endpoint
5. **Whitelist** : IPs autorisées à dépasser les limites

### Optimisations
1. **Cache Redis** : Pour le rate limiting distribué
2. **Indexes** : Optimisation des requêtes de session
3. **Partitioning** : Séparation des données invités
4. **CDN** : Limitation au niveau CDN

## Tests

### Tests unitaires
```python
# Exemple de test
def test_guest_session_creation():
    session = create_guest_session('127.0.0.1')
    assert session.can_create_document() == True
    assert session.documents_created == 0
```

### Tests d'intégration
- Upload de document en mode invité
- Vérification des limites
- Rate limiting
- Nettoyage automatique

## Déploiement

### Prérequis
1. Cache Django configuré
2. Base de données avec indexes
3. Logs configurés
4. Commande de nettoyage programmée (cron)

### Checklist
- [ ] Migrations appliquées
- [ ] Cache configuré
- [ ] Logs activés
- [ ] Commande de nettoyage programmée
- [ ] Tests passés
- [ ] Monitoring configuré

## Support

### Dépannage
1. **Sessions non créées** : Vérifier la base de données
2. **Rate limiting** : Vérifier le cache
3. **Nettoyage** : Vérifier les logs
4. **Performance** : Vérifier les indexes

### Contact
- Développeur : [Votre nom]
- Documentation : Ce fichier
- Issues : [Lien vers le dépôt]
