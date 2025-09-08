import os
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.tool_converter import convert_crewai_tools_to_langchain

try:
    print("✅ Modern LangChain stack with AgentExecutor imported successfully")
except Exception as e:
    print(f"❌ Import error in sage_agent: {e}")

from src.tools.sage_tools import SAGE_TOOLS
from src.tools.document_tools import (
    DocumentAnalysisTool, InvoiceExtractionTool, ClientImportTool, 
    ProductImportTool, DocumentValidationTool
)

class SageAgentManager:
    """Gestionnaire des agents IA pour Sage Business Cloud Accounting"""
    
    def __init__(self):
        print("🔧 Initializing SageAgentManager...")
        try:
            # Configuration du modèle LLM avec ChatOpenAI (programmer's approach + my error handling)
            self.llm = None
            self.agents_available = False
            
            # Modern LangChain 0.3.x configuration (expert's Option A)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("⚠️ OPENAI_API_KEY not found - AI agents will be unavailable")
                self.llm = None
            else:
                try:
                    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
                    proxy_url = (os.getenv("HTTPS_PROXY")
                                 or os.getenv("HTTP_PROXY")
                                 or os.getenv("ALL_PROXY"))
                    timeout_s = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))

                    # Modern httpx client with proper proxy configuration (httpx >=0.28.1)
                    if proxy_url:
                        # Use HTTPTransport with proxy (modern httpx 0.28+ pattern)
                        transport = httpx.HTTPTransport(proxy=proxy_url)
                        http_client = httpx.Client(transport=transport, timeout=timeout_s)
                    else:
                        http_client = httpx.Client(timeout=timeout_s)

                    self.llm = ChatOpenAI(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        api_key=api_key,
                        base_url=base_url,
                        http_client=http_client,
                        temperature=0.1,
                        max_tokens=2000,
                    )
                    self.agents_available = True
                    print(f"✅ Modern LLM configured (model={os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}, base_url={base_url}, proxy={'yes' if proxy_url else 'no'})")
                    
                except Exception as e:
                    print(f"❌ Error configuring modern LLM: {e}")
                    self.llm = None
                    
        except Exception as e:
            print(f"❌ Error initializing SageAgentManager: {e}")
            self.llm = None
            self.agents_available = False
        
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
        
        # Configurer les agents LangChain avec outils (Option A moderne)
        if self.agents_available:
            self.langchain_tools = self._convert_tools_to_langchain()
            self.agents = self._create_langchain_agents()
            print("✅ Modern LangChain agents with tools configured successfully")
        else:
            self.langchain_tools = []
            self.agents = {}
            print("❌ AI agents not configured - LLM unavailable")
    
    def _convert_tools_to_langchain(self):
        """Convertit les outils CrewAI en outils LangChain compatibles"""
        try:
            all_tools = self.sage_tools + self.document_tools
            langchain_tools = convert_crewai_tools_to_langchain(all_tools)
            print(f"✅ Converted {len(langchain_tools)} tools to LangChain format")
            return langchain_tools
        except Exception as e:
            print(f"❌ Error converting tools: {e}")
            return []
    
    def _create_langchain_agents(self):
        """Crée les agents LangChain avec AgentExecutor"""
        if not self.llm or not self.langchain_tools:
            print("❌ Cannot create LangChain agents - missing LLM or tools")
            return {}
        
        try:
            agents = {}
            
            # Agent Comptable
            comptable_prompt = ChatPromptTemplate.from_messages([
                ("system", """Vous êtes un assistant comptable expert avec une connaissance approfondie de Sage Business Cloud Accounting. 
                Vous excellez dans la gestion des clients, fournisseurs, factures, et produits. Vous savez également analyser des documents 
                (factures PDF, images, fichiers CSV/Excel) pour extraire automatiquement les données comptables et les intégrer dans Sage.
                
                Vos spécialités incluent:
                - Création et gestion des fiches clients et fournisseurs
                - Saisie et traitement des factures
                - Gestion du catalogue produits
                - Analyse automatique de documents comptables
                - Import en masse de données depuis des fichiers
                - Validation et contrôle de cohérence des données
                
                IMPORTANT: Utilisez les outils Sage disponibles pour effectuer des actions réelles dans le système.
                
                Si la demande implique une CRÉATION, MODIFICATION ou SUPPRESSION dans Sage:
                - Préparez le plan d'action détaillé
                - Expliquez exactement ce que vous allez faire
                - Terminez par: "PLANNED_ACTION: [type:create_client/create_invoice/etc.] [description:détails]"
                
                Pour les CONSULTATIONS (lister, afficher, rechercher), utilisez directement les outils Sage."""),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            comptable_agent = create_openai_functions_agent(self.llm, self.langchain_tools, comptable_prompt)
            agents['comptable'] = AgentExecutor(agent=comptable_agent, tools=self.langchain_tools, verbose=True)
            
            # Agent Analyste (version simplifiée avec les mêmes outils)
            analyste_prompt = ChatPromptTemplate.from_messages([
                ("system", """Vous êtes un analyste financier senior spécialisé dans l'interprétation des données comptables de Sage Business Cloud Accounting.
                
                Vos compétences incluent:
                - Génération et analyse des bilans comptables
                - Création de comptes de résultat détaillés
                - Calcul et interprétation des KPIs financiers
                - Recherche et analyse de transactions
                - Validation de la qualité des données extraites de documents
                
                IMPORTANT: Utilisez les outils Sage disponibles pour accéder aux données réelles."""),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            analyste_agent = create_openai_functions_agent(self.llm, self.langchain_tools, analyste_prompt)
            agents['analyste'] = AgentExecutor(agent=analyste_agent, tools=self.langchain_tools, verbose=True)
            
            # Agent Support
            support_prompt = ChatPromptTemplate.from_messages([
                ("system", """Vous êtes un expert en support technique et formation pour Sage Business Cloud Accounting.
                
                Vos domaines d'expertise:
                - Formation et accompagnement des utilisateurs
                - Résolution de problèmes techniques
                - Explication des fonctionnalités Sage
                - Guide d'utilisation du traitement automatique de documents
                - Bonnes pratiques comptables et organisationnelles
                
                IMPORTANT: Utilisez les outils Sage disponibles pour démontrer les fonctionnalités."""),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            support_agent = create_openai_functions_agent(self.llm, self.langchain_tools, support_prompt)
            agents['support'] = AgentExecutor(agent=support_agent, tools=self.langchain_tools, verbose=True)
            
            print(f"✅ Created {len(agents)} LangChain agents with tools")
            return agents
            
        except Exception as e:
            print(f"❌ Error creating LangChain agents: {e}")
            return {}
    
    def _create_system_prompts(self):
        """Crée les prompts système pour différents types d'agents (sans CrewAI)"""
        
        if not self.llm:
            print("❌ Cannot create system prompts - LLM not available")
            return {}
        
        try:
            # Prompt pour l'Assistant Comptable Expert
            comptable_prompt = """Vous êtes un assistant comptable expert avec une connaissance approfondie de Sage Business Cloud Accounting. 
            Vous excellez dans la gestion des clients, fournisseurs, factures, et produits. Vous savez également analyser des documents 
            (factures PDF, images, fichiers CSV/Excel) pour extraire automatiquement les données comptables et les intégrer dans Sage.
            
            Vos spécialités incluent:
            - Création et gestion des fiches clients et fournisseurs
            - Saisie et traitement des factures
            - Gestion du catalogue produits
            - Analyse automatique de documents comptables
            - Import en masse de données depuis des fichiers
                - Validation et contrôle de cohérence des données
                
                Vous communiquez de manière claire et professionnelle, en expliquant chaque étape de vos actions.
                
                IMPORTANT: Utilisez les outils Sage disponibles pour effectuer des actions réelles dans le système."""
            
            # Prompt pour l'Analyste Financier Senior
            analyste_prompt = """Vous êtes un analyste financier senior spécialisé dans l'interprétation des données comptables de Sage Business Cloud Accounting.
                Vous excellez dans la production de rapports financiers, l'analyse de performance et la validation de données.
                
                Vos compétences incluent:
                - Génération et analyse des bilans comptables
                - Création de comptes de résultat détaillés
                - Calcul et interprétation des KPIs financiers
                - Recherche et analyse de transactions
                - Validation de la qualité des données extraites de documents
                - Détection d'incohérences et recommandations d'amélioration
                - Conseil en optimisation fiscale et gestion de la TVA
                
                Vous présentez vos analyses de manière structurée avec des recommandations concrètes.
                
                IMPORTANT: Utilisez les outils Sage disponibles pour accéder aux données réelles."""
            
            # Prompt pour l'Expert Support Sage
            support_prompt = """Vous êtes un expert en support technique et formation pour Sage Business Cloud Accounting.
                Vous aidez les utilisateurs à comprendre et utiliser efficacement le système, y compris les nouvelles fonctionnalités de traitement de documents.
                
                Vos domaines d'expertise:
                - Formation et accompagnement des utilisateurs
                - Résolution de problèmes techniques
                - Explication des fonctionnalités Sage
                - Guide d'utilisation du traitement automatique de documents
                - Bonnes pratiques comptables et organisationnelles
                - Optimisation des workflows
                - Assistance pour l'import et l'export de données
                
                Vous êtes patient, pédagogue et vous adaptez vos explications au niveau de l'utilisateur.
                
                IMPORTANT: Utilisez les outils Sage disponibles pour démontrer les fonctionnalités."""
            
            return {
                'comptable': comptable_prompt,
                'analyste': analyste_prompt,
                'support': support_prompt
            }
            
        except Exception as e:
            print(f"❌ Error creating system prompts: {e}")
            return {}
    
    def process_user_request(self, user_message: str, user_id: int = None, conversation_context: list = None) -> str:
        """Traite une demande utilisateur avec LangChain moderne (sans CrewAI)"""
        
        # Check if LLM is available
        if not self.agents_available or not self.llm:
            return "❌ L'agent IA n'est pas disponible. Veuillez vérifier que la clé OpenAI API est configurée."
        
        try:
            # Récupérer les credentials Sage de l'utilisateur
            sage_credentials = None
            if user_id:
                try:
                    from src.models.user import User
                    user = User.query.get(user_id)
                    if user and hasattr(user, 'sage_credentials_encrypted') and user.sage_credentials_encrypted:
                        sage_credentials = user.get_sage_credentials()
                except Exception as e:
                    print(f"Warning: Could not get user credentials: {e}")
            
            # Injecter les credentials dans les outils Sage
            if sage_credentials:
                try:
                    from src.tools.sage_tools import set_user_credentials
                    set_user_credentials(sage_credentials)
                except Exception as e:
                    print(f"Warning: Could not set Sage credentials: {e}")
            
            # Analyser le message pour déterminer l'agent approprié  
            agent_type = self._determine_agent_type(user_message)
            selected_agent = self.agents.get(agent_type)
            
            if not selected_agent:
                return f"❌ Agent '{agent_type}' non disponible."
            
            # Créer le contexte de la tâche avec les credentials
            task_context = self._build_task_context(user_message, conversation_context, user_id, sage_credentials)
            
            # Construire l'input pour l'agent LangChain avec contexte
            agent_input = f"""Contexte utilisateur: {task_context}
            
            Demande: {user_message}
            
            Instructions:
            1. Analysez la demande de l'utilisateur
            2. Si la demande concerne un document (analyse, extraction, import), utilisez d'abord les outils de traitement de documents appropriés  
            3. Utilisez ensuite les outils Sage nécessaires pour répondre à la demande
            4. IMPORTANT: Si la demande implique une CRÉATION, MODIFICATION ou SUPPRESSION dans Sage (clients, factures, produits, etc.), 
               NE PAS exécuter l'action immédiatement. Au lieu de cela:
               - Préparez le plan d'action détaillé
               - Expliquez exactement ce que vous allez faire
               - Terminez par: "PLANNED_ACTION: [type:create_client/create_invoice/etc.] [description:détails de l'action]"
            5. Pour les CONSULTATIONS (lister, afficher, rechercher), utilisez directement les outils Sage sans demander confirmation
            6. Fournissez une réponse complète et professionnelle
            7. Si vous analysez des documents, fournissez un résumé des données extraites et leur qualité
            
            Répondez de manière claire et structurée en français.
            """
            
            # Exécuter l'agent LangChain avec les outils
            result = selected_agent.invoke({
                "input": agent_input,
                "chat_history": []  # Peut être étendu pour inclure l'historique
            })
            
            result_str = result.get('output', str(result))
            
            # Check if the agent planned an action instead of executing it
            if "PLANNED_ACTION:" in result_str:
                return self.parse_planned_action(result_str)
            
            return result_str
            
        except Exception as e:
            error_msg = f"Erreur lors du traitement de votre demande: {str(e)}. Veuillez réessayer ou reformuler votre question."
            print(f"❌ Error in process_user_request: {e}")
            return error_msg
    
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
        if not self.agents_available:
            return {
                'status': 'unavailable',
                'message': 'AI agents not available - check OpenAI API key and dependencies',
                'comptable': {'tools': 0},
                'analyste': {'tools': 0},
                'support': {'tools': 0}
            }
        
        return {
            'status': 'available',
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
                'tools': len(self.sage_tools + self.document_tools) if self.agents else 0
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
                'tools': (len(self.sage_tools) + 2) if self.agents else 0
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
                'tools': 5 if self.agents else 0
            }
        }
    
    def is_available(self) -> bool:
        """Check if agents are available"""
        return self.agents_available and len(self.agents) > 0
    
    def parse_planned_action(self, result_str: str) -> dict:
        """Parse the agent response to extract planned action details"""
        import re
        
        # Find the PLANNED_ACTION marker
        action_match = re.search(r'PLANNED_ACTION:\s*\[type:(.*?)\]\s*\[description:(.*?)\]', result_str)
        
        if action_match:
            action_type = action_match.group(1).strip()
            action_description = action_match.group(2).strip()
            
            # Extract the main response (everything before PLANNED_ACTION)
            main_response = result_str.split('PLANNED_ACTION:')[0].strip()
            
            # Extract details if possible
            details = self.extract_action_details(main_response, action_type)
            
            return {
                'response': main_response,
                'agent_type': 'comptable_with_confirmation',
                'capabilities_used': ['analysis', 'sage_planning'],
                'success': True,
                'planned_action': {
                    'type': action_type,
                    'description': action_description,
                    'details': details
                }
            }
        
        # Fallback if parsing fails
        return {
            'response': result_str,
            'agent_type': 'comptable',
            'capabilities_used': ['analysis'],
            'success': True
        }
    
    def extract_action_details(self, response: str, action_type: str) -> dict:
        """Extract specific details from the agent response based on action type"""
        details = {}
        
        response_lower = response.lower()
        
        # Extract client details
        if 'client' in action_type:
            if 'nom' in response_lower or 'client' in response_lower:
                # Try to extract client name
                import re
                name_patterns = [
                    r'client[:\s]*([^\n]+)',
                    r'nom[:\s]*([^\n]+)',
                    r'pour\s+([A-Za-z\s]+)',
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, response, re.IGNORECASE)
                    if match:
                        details['client_name'] = match.group(1).strip()
                        break
        
        # Extract invoice details
        elif 'invoice' in action_type or 'facture' in action_type:
            import re
            # Extract amounts
            amount_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*€', response)
            if amount_match:
                details['amount'] = amount_match.group(1)
            
            # Extract client for invoice
            client_patterns = [
                r'pour\s+([A-Za-z\s]+)',
                r'client[:\s]*([^\n]+)',
            ]
            for pattern in client_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    details['client_name'] = match.group(1).strip()
                    break
        
        # Extract product details
        elif 'product' in action_type or 'produit' in action_type:
            import re
            # Extract product name
            prod_patterns = [
                r'produit[:\s]*([^\n]+)',
                r'nom[:\s]*([^\n]+)',
            ]
            for pattern in prod_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    details['product_name'] = match.group(1).strip()
                    break
            
            # Extract price
            price_match = re.search(r'prix[:\s]*(\d+(?:,\d+)?(?:\.\d+)?)\s*€', response, re.IGNORECASE)
            if price_match:
                details['price'] = price_match.group(1)
        
        return details

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
    
    def is_available(self) -> bool:
        """Check if agents are available"""
        return self.manager.is_available()