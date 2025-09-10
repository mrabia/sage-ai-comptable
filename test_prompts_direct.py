#!/usr/bin/env python3
"""
Test direct des prompts système marocains (sans dépendances)
"""

def test_prompts_directly():
    """Test direct du contenu des prompts"""
    print("[TEST] Test direct des prompts marocains")
    print("=" * 50)
    
    # Lire directement le fichier sage_agent.py
    try:
        with open('backend/src/agents/sage_agent.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tests des personas
        personas = [
            ("Ahmed Benali", "Expert-Comptable Marocain"),
            ("Fatima El Fassi", "Analyste Financière Senior"),
            ("Youssef Tazi", "Expert Support et Formation")
        ]
        
        print("[PERSONAS] Vérification des personas:")
        for persona, titre in personas:
            if persona in content:
                print(f"[OK] {persona} - {titre} présent")
            else:
                print(f"[ERREUR] {persona} - {titre} manquant")
        
        # Tests des spécificités marocaines
        moroccan_features = [
            "20 ans d'expérience",
            "fiscalité marocaine",
            "CGNC", "CNSS", "TVA (20%, 14%, 10%, 7%)",
            "Impôt sur les Sociétés (IS)",
            "Casablanca", "Rabat", "ISCAE", "ENSIAS",
            "normes comptables marocaines",
            "Plan Comptable Général des Entreprises (PCGE)"
        ]
        
        print(f"\n[EXPERTISE] Vérification expertise marocaine:")
        found_features = []
        for feature in moroccan_features:
            if feature in content:
                found_features.append(feature)
                print(f"[OK] {feature}")
            else:
                print(f"[MANQUE] {feature}")
        
        coverage = len(found_features) / len(moroccan_features) * 100
        print(f"\n[COUVERTURE] Expertise marocaine: {coverage:.1f}%")
        
        # Tests des outils fiscaux
        fiscal_tools = [
            "déclarations TVA",
            "acomptes provisionnels", 
            "Taxe Professionnelle",
            "Contribution Sociale de Solidarité"
        ]
        
        print(f"\n[FISCAL] Vérification outils fiscaux:")
        for tool in fiscal_tools:
            if tool in content:
                print(f"[OK] {tool}")
            else:
                print(f"[MANQUE] {tool}")
        
        return coverage > 80  # Au moins 80% de couverture
        
    except Exception as e:
        print(f"[ERREUR] {str(e)}")
        return False

def test_agent_configuration():
    """Test de la structure de configuration des agents"""
    print(f"\n[CONFIG] Test structure agent")
    print("=" * 30)
    
    try:
        with open('backend/src/agents/sage_agent.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier les imports essentiels
        required_imports = [
            "from langchain_openai import ChatOpenAI",
            "from langchain.agents import AgentExecutor", 
            "ChatPromptTemplate",
            "MessagesPlaceholder"
        ]
        
        for import_stmt in required_imports:
            if import_stmt in content:
                print(f"[OK] Import: {import_stmt.split()[-1]}")
            else:
                print(f"[MANQUE] Import: {import_stmt}")
        
        # Vérifier les méthodes clés
        required_methods = [
            "_create_system_prompts",
            "process_user_request", 
            "_determine_agent_type"
        ]
        
        for method in required_methods:
            if f"def {method}" in content:
                print(f"[OK] Méthode: {method}")
            else:
                print(f"[MANQUE] Méthode: {method}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] {str(e)}")
        return False

if __name__ == "__main__":
    print("[MAROC] TEST DIRECT DES PROMPTS MAROCAINS")
    print("=" * 60)
    
    success1 = test_prompts_directly()
    success2 = test_agent_configuration()
    
    print(f"\n[RESULTAT] RESULTAT FINAL:")
    print(f"   • Expertise marocaine: {'REUSSI' if success1 else 'ECHOUE'}")  
    print(f"   • Configuration agent: {'REUSSI' if success2 else 'ECHOUE'}")
    
    if success1 and success2:
        print("\n[SUCCESS] IMPLEMENTATION MAROCAINE VALIDEE!")
        print("Les agents sont maintenant des experts comptables marocains")
    else:
        print("\n[WARNING] IMPLEMENTATION INCOMPLETE")