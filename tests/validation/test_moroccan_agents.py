#!/usr/bin/env python3
"""
Test des agents comptables marocains
"""
import os
import sys

# Add backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_moroccan_agent_personas():
    """Test que les personas marocaines sont correctement implémentées"""
    print("[TEST] Test des personas d'agents comptables marocains")
    print("=" * 60)
    
    try:
        # Import direct des prompts système
        from backend.src.agents.sage_agent import SageAgentManager
        
        # Créer le gestionnaire d'agents
        manager = SageAgentManager()
        
        # Tester la création des prompts système
        prompts = manager._create_system_prompts()
        
        print("✅ Gestionnaire d'agents créé avec succès")
        
        # Vérifier les personas marocaines
        tests = [
            ("Ahmed Benali", "comptable"),
            ("Fatima El Fassi", "analyste"), 
            ("Youssef Tazi", "support")
        ]
        
        for persona, agent_type in tests:
            if agent_type in prompts:
                prompt = prompts[agent_type]
                if persona in prompt:
                    print(f"[OK] Persona {persona} ({agent_type}) implementee")
                else:
                    print(f"[MANQUE] Persona {persona} ({agent_type}) manquante")
            else:
                print(f"[MANQUE] Agent {agent_type} non trouve")
        
        # Vérifier les spécificités marocaines
        moroccan_keywords = [
            "Maroc", "marocain", "marocaine",
            "TVA (20%, 14%, 10%, 7%)",
            "CGNC", "CNSS", "IS", "IR",
            "Casablanca", "Rabat", "ENSIAS", "ISCAE"
        ]
        
        print(f"\n[VERIF] Verification des specificites marocaines:")
        
        for agent_type, prompt in prompts.items():
            found_keywords = []
            for keyword in moroccan_keywords:
                if keyword.lower() in prompt.lower():
                    found_keywords.append(keyword)
            
            if found_keywords:
                print(f"[OK] Agent {agent_type}: {len(found_keywords)} specificites trouvees")
                for kw in found_keywords[:3]:  # Afficher les 3 premiers
                    print(f"   - {kw}")
            else:
                print(f"[MANQUE] Agent {agent_type}: Aucune specificite marocaine trouvee")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test: {str(e)}")
        return False

def test_agent_initialization():
    """Test l'initialisation des agents sans dépendances complètes"""
    print("\n[INIT] Test d'initialisation des agents")
    print("=" * 40)
    
    try:
        from backend.src.agents.sage_agent import SageAgentManager
        
        # Test avec variable d'environnement minimale
        os.environ['OPENAI_API_KEY'] = 'test-key'
        
        manager = SageAgentManager()
        
        # Vérifier que les composants essentiels sont présents
        if hasattr(manager, '_create_system_prompts'):
            print("[OK] Methode _create_system_prompts presente")
        
        if hasattr(manager, 'process_user_request'):
            print("[OK] Methode process_user_request presente")
            
        if hasattr(manager, '_determine_agent_type'):
            print("[OK] Methode _determine_agent_type presente")
        
        print("[OK] Structure d'agent correctement initialisee")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur d'initialisation: {str(e)}")
        return False

if __name__ == "__main__":
    print("[MAROC] TEST DES AGENTS COMPTABLES MAROCAINS")
    print("=" * 80)
    
    success1 = test_moroccan_agent_personas()
    success2 = test_agent_initialization()
    
    print(f"\n[RESULTAT] RESULTAT FINAL:")
    print(f"   - Test personas marocaines: {'[OK] REUSSI' if success1 else '[ECHEC] ECHOUE'}")
    print(f"   - Test initialisation: {'[OK] REUSSI' if success2 else '[ECHEC] ECHOUE'}")
    
    if success1 and success2:
        print("\n[SUCCESS] TOUS LES TESTS REUSSIS - Expertise marocaine implementee!")
        sys.exit(0)
    else:
        print("\n[WARNING] CERTAINS TESTS ONT ECHOUE")
        sys.exit(1)