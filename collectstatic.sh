#!/bin/bash
# Script pour collecter les fichiers statiques avant le déploiement

echo "🔧 Collecte des fichiers statiques..."

# Activer l'environnement virtuel si disponible
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Environnement virtuel activé"
fi

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

echo "✅ Fichiers statiques collectés avec succès"
echo "📁 Fichiers disponibles dans: staticfiles/"
