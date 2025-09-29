"""
Service pour l'intégration avec l'API OpenAI
"""
import os
import openai
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_questions_from_document(self, file_path, document_title, question_count=5, difficulty='medium', education_level=''):
        """
        Génère des questions QCM à partir d'un fichier directement transmis à l'IA
        """
        try:
            import base64
            
            logger.info(f"🚀 Début de génération IA pour le document: {document_title}")
            logger.info(f"📁 Chemin du fichier: {file_path}")
            logger.info(f"📊 Paramètres: {question_count} questions, difficulté {difficulty}, niveau {education_level}")
            
            # Construire le contexte éducatif détaillé
            education_context = self._build_education_context(education_level)
            
            # Lire le fichier et l'encoder en base64
            logger.info(f"📖 Lecture du fichier: {file_path}")
            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            logger.info(f"📏 Taille du fichier: {len(file_data)} bytes")
            logger.info(f"📏 Taille base64: {len(file_base64)} caractères")
            
            # Déterminer le type MIME du fichier
            file_extension = os.path.splitext(file_path)[1].lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.json': 'application/json',
                '.csv': 'text/csv',
                '.xml': 'application/xml',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            mime_type = mime_types.get(file_extension, 'application/octet-stream')
            logger.info(f"🏷️ Extension: {file_extension}, Type MIME: {mime_type}")
            
            # Prompt pour générer des questions QCM
            prompt = f"""
Tu es un expert en pédagogie et en didactique. Génère {question_count} questions à choix multiples (QCM) de haute qualité basées sur le document suivant.

Titre du document: {document_title}

{education_context}

Instructions détaillées:
- Génère exactement {question_count} questions QCM
- Niveau de difficulté demandé: {difficulty}
- Chaque question doit avoir 4 options (A, B, C, D)
- Une seule réponse correcte par question
- Les questions doivent tester différents niveaux de compréhension :
  * Mémorisation (faits, définitions)
  * Compréhension (explications, relations)
  * Application (utilisation des concepts)
  * Analyse (comparaison, distinction)

Qualité des questions:
- Utilise un vocabulaire adapté au niveau d'éducation
- Les distracteurs (mauvaises réponses) doivent être plausibles mais incorrects
- Évite les questions trop évidentes ou piégeuses
- Varie les types de questions (définition, application, calcul, etc.)
- Assure-toi que la réponse correcte est clairement la meilleure

Format de réponse: JSON avec la structure suivante:
{{
    "questions": [
        {{
            "question_text": "Texte de la question claire et précise",
            "difficulty": "{difficulty}",
            "answers": [
                {{"text": "Option A - réponse plausible", "is_correct": true}},
                {{"text": "Option B - distracteur plausible", "is_correct": false}},
                {{"text": "Option C - distracteur plausible", "is_correct": false}},
                {{"text": "Option D - distracteur plausible", "is_correct": false}}
            ]
        }}
    ]
}}

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire.
"""

            # Uploader le fichier d'abord
            logger.info(f"📤 Upload du fichier vers OpenAI...")
            uploaded_file = self.client.files.create(
                file=open(file_path, 'rb'),
                purpose='assistants'
            )
            logger.info(f"✅ Fichier uploadé avec l'ID: {uploaded_file.id}")
            
            # Construire le message avec le fichier
            message_content = [
                {"type": "text", "text": prompt}
            ]
            
            # Ajouter le fichier selon son type
            if file_extension in ['.pdf', '.txt', '.md', '.json', '.csv', '.xml', '.docx', '.pptx', '.xlsx']:
                # Pour les documents, utiliser le type "file"
                logger.info(f"📄 Ajout du document de type: {mime_type}")
                message_content.append({
                    "type": "file",
                    "file": {
                        "file_id": uploaded_file.id
                    }
                })
            else:
                # Pour les images, utiliser le type "image_url"
                logger.info(f"🖼️ Ajout de l'image de type: {mime_type}")
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{file_base64}"
                    }
                })

            logger.info(f"🤖 Envoi de la requête à OpenAI avec le modèle gpt-4o-mini")
            logger.info(f"📝 Contenu du message: {len(message_content)} éléments")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu es un expert en pédagogie, didactique et évaluation. Tu génères des questions de quiz de haute qualité, adaptées au niveau d'éducation de l'utilisateur. Tu maîtrises les principes de la taxonomie de Bloom et adaptes le vocabulaire et la complexité selon le public cible."},
                    {"role": "user", "content": message_content}
                ],
                max_tokens=2500,
                temperature=0.6
            )
            
            logger.info(f"✅ Réponse reçue d'OpenAI")
            
            # Extraire le contenu de la réponse
            content = response.choices[0].message.content.strip()
            logger.info(f"📄 Contenu brut reçu: {content[:200]}...")
            
            # Nettoyer le contenu (enlever les markdown si présent)
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            logger.info(f"🧹 Contenu nettoyé: {content[:200]}...")
            
            # Parser le JSON
            questions_data = json.loads(content)
            logger.info(f"✅ JSON parsé avec succès, {len(questions_data['questions'])} questions générées")
            
            # Nettoyer le fichier uploadé
            try:
                self.client.files.delete(uploaded_file.id)
                logger.info(f"🗑️ Fichier temporaire supprimé: {uploaded_file.id}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Impossible de supprimer le fichier temporaire: {cleanup_error}")
            
            return questions_data['questions']
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            logger.error(f"Contenu reçu: {content}")
            raise Exception(f"Erreur de parsing JSON de la réponse IA: {e}")
            
        except Exception as e:
            logger.error(f"Erreur OpenAI: {e}")
            # Nettoyer le fichier uploadé en cas d'erreur
            try:
                if 'uploaded_file' in locals():
                    self.client.files.delete(uploaded_file.id)
                    logger.info(f"🗑️ Fichier temporaire supprimé après erreur: {uploaded_file.id}")
            except:
                pass
            raise Exception(f"Erreur lors de la génération des questions par l'IA: {e}")
    
    def _build_education_context(self, education_level):
        """Construit un contexte éducatif détaillé basé sur le niveau d'éducation"""
        if not education_level:
            return "Niveau d'éducation: Non spécifié - Adapte le contenu à un niveau général."
        
        # Mapping des niveaux vers des contextes détaillés
        education_contexts = {
            # Collège
            "6ème": "Niveau: 6ème (11-12 ans) - Utilise un vocabulaire simple, des concepts concrets, évite le jargon technique. Questions basées sur la mémorisation et la compréhension de base.",
            "5ème": "Niveau: 5ème (12-13 ans) - Vocabulaire accessible, concepts progressivement plus abstraits. Mélange mémorisation et compréhension.",
            "4ème": "Niveau: 4ème (13-14 ans) - Vocabulaire de niveau collège, introduction de concepts plus complexes. Questions de compréhension et d'application basique.",
            "3ème": "Niveau: 3ème (14-15 ans) - Vocabulaire de fin de collège, concepts abstraits maîtrisés. Questions d'application et d'analyse simple.",
            
            # Lycée
            "2nde": "Niveau: 2nde (15-16 ans) - Vocabulaire lycéen, concepts abstraits. Questions de compréhension, application et analyse.",
            "1ère": "Niveau: 1ère (16-17 ans) - Vocabulaire spécialisé selon la matière, concepts avancés. Questions d'analyse et de synthèse.",
            "Terminale": "Niveau: Terminale (17-18 ans) - Vocabulaire expert, concepts complexes. Questions d'analyse, synthèse et évaluation.",
            "Bac Pro": "Niveau: Bac Pro - Vocabulaire professionnel, applications concrètes. Questions pratiques et techniques.",
            "Bac Techno": "Niveau: Bac Techno - Vocabulaire technique spécialisé, applications sectorielles. Questions techniques et appliquées.",
            "CAP": "Niveau: CAP - Vocabulaire professionnel de base, applications pratiques. Questions concrètes et opérationnelles.",
            
            # Supérieur
            "BTS": "Niveau: BTS - Vocabulaire professionnel avancé, applications sectorielles. Questions techniques et professionnelles.",
            "DUT": "Niveau: DUT - Vocabulaire technique spécialisé, applications industrielles. Questions techniques et méthodologiques.",
            "BUT": "Niveau: BUT - Vocabulaire technique expert, applications professionnelles. Questions techniques avancées et méthodologiques.",
            "Licence": "Niveau: Licence - Vocabulaire académique, concepts théoriques. Questions d'analyse, synthèse et critique.",
            "Licence Pro": "Niveau: Licence Pro - Vocabulaire professionnel expert, applications avancées. Questions techniques et managériales.",
            "Master": "Niveau: Master - Vocabulaire académique expert, concepts avancés. Questions de recherche, analyse critique et innovation.",
            "Master Pro": "Niveau: Master Pro - Vocabulaire professionnel expert, applications stratégiques. Questions de management et d'innovation.",
            "Doctorat": "Niveau: Doctorat - Vocabulaire scientifique expert, concepts de pointe. Questions de recherche, innovation et contribution au savoir.",
            "École d'ingénieur": "Niveau: École d'ingénieur - Vocabulaire technique expert, applications industrielles. Questions techniques, méthodologiques et d'innovation.",
            "École de commerce": "Niveau: École de commerce - Vocabulaire business expert, applications stratégiques. Questions de management, stratégie et leadership.",
            "École spécialisée": "Niveau: École spécialisée - Vocabulaire expert du domaine, applications professionnelles. Questions spécialisées et pratiques.",
            "Formation continue": "Niveau: Formation continue - Vocabulaire professionnel adapté, applications pratiques. Questions opérationnelles et d'amélioration.",
            
            # Professionnel
            "En activité": "Niveau: Professionnel en activité - Vocabulaire professionnel, applications pratiques. Questions opérationnelles et d'efficacité.",
            "En recherche d'emploi": "Niveau: Professionnel en recherche - Vocabulaire professionnel, applications pratiques. Questions de compétences et d'adaptation.",
            "Retraité": "Niveau: Retraité - Vocabulaire accessible, applications concrètes. Questions de compréhension et d'application basique.",
            
            # Autre
            "Autre": "Niveau: Autre - Adapte le contenu à un niveau général accessible. Questions de compréhension et d'application."
        }
        
        return education_contexts.get(education_level, f"Niveau: {education_level} - Adapte le contenu à ce niveau spécifique.")
    
    def _get_fallback_questions(self, document_title, question_count, difficulty):
        """
        Questions de secours en cas d'erreur avec l'API
        """
        fallback_questions = [
            {
                "question_text": f"Quel est le sujet principal du document '{document_title}' ?",
                "difficulty": difficulty,
                "answers": [
                    {"text": "Le sujet principal du document", "is_correct": True},
                    {"text": "Un sujet secondaire", "is_correct": False},
                    {"text": "Une information accessoire", "is_correct": False},
                    {"text": "Une conclusion", "is_correct": False}
                ]
            },
            {
                "question_text": f"Le document '{document_title}' contient-il des informations importantes ?",
                "difficulty": difficulty,
                "answers": [
                    {"text": "Oui, des informations importantes", "is_correct": True},
                    {"text": "Non, aucune information", "is_correct": False},
                    {"text": "Seulement des détails", "is_correct": False},
                    {"text": "Des informations obsolètes", "is_correct": False}
                ]
            }
        ]
        
        # Retourner le nombre demandé de questions
        return fallback_questions[:question_count]
