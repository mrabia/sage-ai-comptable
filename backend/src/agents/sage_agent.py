import os
from crewai import Agent, Task, Crew, LLM
from src.tools.sage_tools import SAGE_TOOLS
from src.tools.document_tools import (
    DocumentAnalysisTool, InvoiceExtractionTool, ClientImportTool, 
    ProductImportTool, DocumentValidationTool
)

class SageAgentManager:
    """Gestionnaire des agents IA pour Sage Business Cloud Accounting"""
    
    def __init__(self):
        # Configuration du modèle LLM
        self.llm = LLM(
            model="gpt-4.1-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")
        )
        
        # Initialiser les outils Sage (utiliser la liste existante)
        self.sage_tools = SAGE_TOOLS
        
        # Initialiser les outils de traitement de documents
        self.document_tools = [
            DocumentAnalysisTool(),
            InvoiceExtractionTool(),
            ClientImportTool(),
            ProductImportTool(),
            DocumentValidationTool()
        ]
        
        # Créer les agents spécialisés
        self.agents = self._create_agents()
    
    def _create_agents(self):
        """Crée les agents spécialisés"""
        
        # Agent Comptable - Gestion des opérations comptables de base + documents
        comptable_agent = Agent(
            role="Assistant Comptable Expert",
            goal="Gérer les opérations comptables courantes, analyser les documents et automatiser la saisie de données dans Sage Business Cloud Accounting",
            backstory="""Vous êtes un assistant comptable expert avec une connaissance approfondie de Sage Business Cloud Accounting. 
            Vous excellez dans la gestion des clients, fournisseurs, factures, et produits. Vous savez également analyser des documents 
            (factures PDF, images, fichiers CSV/Excel) pour extraire automatiquement les données comptables et les intégrer dans Sage.
            
            Vos spécialités incluent:
            - Création et gestion des fiches clients et fournisseurs
            - Saisie et traitement des factures
            - Gestion du catalogue produits
            - Analyse automatique de documents comptables
            - Import en masse de données depuis des fichiers
            - Validation et contrôle de cohérence des données
            
            Vous communiquez de manière claire et professionnelle, en expliquant chaque étape de vos actions.""",
            verbose=True,
            allow_delegation=False,
            tools=self.sage_tools + self.document_tools,
            llm=self.llm
        )
        
        # Agent Analyste Financier - Rapports et analyses + validation de documents
        analyste_agent = Agent(
            role="Analyste Financier Senior",
            goal="Produire des analyses financières approfondies, des rapports comptables et valider la qualité des données extraites de documents",
            backstory="""Vous êtes un analyste financier senior spécialisé dans l'interprétation des données comptables de Sage Business Cloud Accounting.
            Vous excellez dans la production de rapports financiers, l'analyse de performance et la validation de données.
            
            Vos compétences incluent:
            - Génération et analyse des bilans comptables
            - Création de comptes de résultat détaillés
            - Calcul et interprétation des KPIs financiers
            - Recherche et analyse de transactions
            - Validation de la qualité des données extraites de documents
            - Détection d'incohérences et recommandations d'amélioration
            - Conseil en optimisation fiscale et gestion de la TVA
            
            Vous présentez vos analyses de manière structurée avec des recommandations concrètes.""",
            verbose=True,
            allow_delegation=False,
            tools=self.sage_tools + [DocumentValidationTool(), DocumentAnalysisTool()],
            llm=self.llm
        )
        
        # Agent Support - Aide utilisateur et formation + assistance documents
        support_agent = Agent(
            role="Expert Support Sage",
            goal="Fournir une assistance complète aux utilisateurs de Sage Business Cloud Accounting et les aider avec le traitement de documents",
            backstory="""Vous êtes un expert en support technique et formation pour Sage Business Cloud Accounting.
            Vous aidez les utilisateurs à comprendre et utiliser efficacement le système, y compris les nouvelles fonctionnalités de traitement de documents.
            
            Vos domaines d'expertise:
            - Formation et accompagnement des utilisateurs
            - Résolution de problèmes techniques
            - Explication des fonctionnalités Sage
            - Guide d'utilisation du traitement automatique de documents
            - Bonnes pratiques comptables et organisationnelles
            - Optimisation des workflows
            - Assistance pour l'import et l'export de données
            
            Vous êtes patient, pédagogue et vous adaptez vos explications au niveau de l'utilisateur.""",
            verbose=True,
            allow_delegation=False,
            tools=[DocumentAnalysisTool(), DocumentValidationTool()] + self.sage_tools[:3],  # Outils de base
            llm=self.llm
        )
        
        return {
            'comptable': comptable_agent,
            'analyste': analyste_agent,
            'support': support_agent
        }
    
    def process_user_request(self, user_message: str, user_id: int = None, conversation_context: list = None) -> str:
        """Traite une demande utilisateur et détermine l'agent approprié"""
        
        # Récupérer les credentials Sage de l'utilisateur
        sage_credentials = None
        if user_id:
            from src.models.user import User
            user = User.query.get(user_id)
            if user and user.sage_credentials_encrypted:
                sage_credentials = user.get_sage_credentials()
        
        # Injecter les credentials dans les outils Sage
        if sage_credentials:
            from src.tools.sage_tools import set_user_credentials
            set_user_credentials(sage_credentials)
        
        # Analyser le message pour déterminer l'agent approprié
        agent_type = self._determine_agent_type(user_message)
        selected_agent = self.agents[agent_type]
        
        # Créer le contexte de la tâche avec les credentials
        task_context = self._build_task_context(user_message, conversation_context, user_id, sage_credentials)
        
        # Créer la tâche
        task = Task(
            description=f"""
            Contexte utilisateur: {task_context}
            
            Demande: {user_message}
            
            Instructions:
            1. Analysez la demande de l'utilisateur
            2. Si la demande concerne un document (analyse, extraction, import), utilisez d'abord les outils de traitement de documents appropriés
            3. Utilisez ensuite les outils Sage nécessaires pour répondre à la demande
            4. Fournissez une réponse complète et professionnelle
            5. Si vous créez ou modifiez des données, confirmez les actions effectuées
            6. Si vous analysez des documents, fournissez un résumé des données extraites et leur qualité
            
            Répondez de manière claire et structurée en français.
            """,
            agent=selected_agent,
            expected_output="Une réponse complète et professionnelle à la demande de l'utilisateur, avec confirmation des actions effectuées."
        )
        
        # Créer et exécuter l'équipe
        crew = Crew(
            agents=[selected_agent],
            tasks=[task],
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Erreur lors du traitement de votre demande: {str(e)}. Veuillez réessayer ou reformuler votre question."
    
    def _determine_agent_type(self, user_message: str) -> str:
        """Détermine quel agent utiliser selon le message"""
        message_lower = user_message.lower()
        
        # Mots-clés pour l'agent comptable (opérations + documents)
        comptable_keywords = [
            'créer', 'ajouter', 'nouveau', 'client', 'facture', 'produit', 'fournisseur',
            'saisir', 'enregistrer', 'modifier', 'supprimer', 'import', 'importer',
            'document', 'pdf', 'csv', 'excel', 'fichier', 'analyser', 'extraire',
            'upload', 'télécharger', 'scanner', 'ocr'
        ]
        
        # Mots-clés pour l'analyste financier (rapports + validation)
        analyste_keywords = [
            'bilan', 'compte de résultat', 'rapport', 'analyse', 'kpi', 'performance',
            'chiffre d\'affaires', 'bénéfice', 'perte', 'marge', 'rentabilité',
            'transaction', 'recherche', 'historique', 'valider', 'validation',
            'vérifier', 'contrôle', 'cohérence', 'qualité'
        ]
        
        # Mots-clés pour le support (aide + formation)
        support_keywords = [
            'aide', 'comment', 'expliquer', 'formation', 'apprendre', 'tutoriel',
            'problème', 'erreur', 'bug', 'ne fonctionne pas', 'assistance',
            'guide', 'procédure', 'étapes', 'configuration'
        ]
        
        # Compter les correspondances
        comptable_score = sum(1 for keyword in comptable_keywords if keyword in message_lower)
        analyste_score = sum(1 for keyword in analyste_keywords if keyword in message_lower)
        support_score = sum(1 for keyword in support_keywords if keyword in message_lower)
        
        # Déterminer l'agent avec le score le plus élevé
        if comptable_score >= analyste_score and comptable_score >= support_score:
            return 'comptable'
        elif analyste_score >= support_score:
            return 'analyste'
        else:
            return 'support'
    
    def _build_task_context(self, user_message: str, conversation_context: list = None, user_id: int = None, sage_credentials: dict = None) -> str:
        """Construit le contexte pour la tâche de l'agent"""
        context_parts = []
        
        # Ajouter les credentials Sage si disponibles
        if sage_credentials:
            context_parts.append("✅ CONNEXION SAGE ACTIVE - Vous êtes connecté à Sage Business Cloud Accounting")
            context_parts.append("🔧 OUTILS DISPONIBLES - Utilisez directement les outils Sage (get_customers, create_invoice, get_balance_sheet, etc.) sans demander d'identifiants")
            context_parts.append("📋 INSTRUCTIONS - Répondez directement aux demandes en utilisant les outils Sage appropriés")
        else:
            context_parts.append("⚠️ Aucune connexion Sage détectée - Demander à l'utilisateur de se connecter à Sage d'abord")
        
        if user_id:
            context_parts.append(f"Utilisateur ID: {user_id}")
        
        if conversation_context:
            # Prendre les 3 derniers échanges pour le contexte
            recent_context = conversation_context[-6:] if len(conversation_context) > 6 else conversation_context
            context_parts.append("Contexte de conversation récent:")
            for msg in recent_context:
                role = "Utilisateur" if msg.get('role') == 'user' else "Assistant"
                content = msg.get('content', '')[:200] + "..." if len(msg.get('content', '')) > 200 else msg.get('content', '')
                context_parts.append(f"- {role}: {content}")
        
        return "\n".join(context_parts) if context_parts else "Nouvelle conversation"
    
    def get_agent_capabilities(self) -> dict:
        """Retourne les capacités de chaque agent"""
        return {
            'comptable': {
                'description': 'Assistant Comptable Expert',
                'capabilities': [
                    'Gestion des clients et fournisseurs',
                    'Création et traitement des factures',
                    'Gestion du catalogue produits',
                    'Analyse automatique de documents (PDF, images, CSV, Excel)',
                    'Extraction de données de factures',
                    'Import en masse de clients et produits',
                    'Validation et contrôle de données'
                ],
                'tools': len(self.sage_tools + self.document_tools)
            },
            'analyste': {
                'description': 'Analyste Financier Senior',
                'capabilities': [
                    'Génération de bilans comptables',
                    'Création de comptes de résultat',
                    'Calcul de KPIs financiers',
                    'Recherche et analyse de transactions',
                    'Validation de qualité des données extraites',
                    'Recommandations financières'
                ],
                'tools': len(self.sage_tools) + 2
            },
            'support': {
                'description': 'Expert Support Sage',
                'capabilities': [
                    'Formation et accompagnement utilisateurs',
                    'Résolution de problèmes techniques',
                    'Guide d\'utilisation des fonctionnalités',
                    'Assistance traitement de documents',
                    'Bonnes pratiques comptables',
                    'Optimisation des workflows'
                ],
                'tools': 5
            }
        }

# Classe de compatibilité pour l'ancien code
class SageAccountingAgent:
    """Classe de compatibilité pour l'ancien code"""
    
    def __init__(self):
        self.manager = SageAgentManager()
    
    def execute_task(self, user_message: str, credentials: dict, business_id: str = None, agent_type: str = "accounting") -> str:
        """Méthode de compatibilité"""
        return self.manager.process_user_request(user_message)
    
    def get_agent_capabilities(self) -> dict:
        """Méthode de compatibilité"""
        return self.manager.get_agent_capabilities()
    
    def determine_agent_type(self, user_message: str) -> str:
        """Méthode de compatibilité"""
        return self.manager._determine_agent_type(user_message)

