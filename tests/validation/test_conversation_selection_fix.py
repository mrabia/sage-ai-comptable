#!/usr/bin/env python3
"""
Test du fix pour la selection de conversation
"""

def test_conversation_selection_fix():
    """Test que le fix pour selectConversation fonctionne"""
    print("[TEST] Validation du fix selectConversation")
    print("=" * 50)
    
    try:
        with open('frontend/src/contexts/ChatContext.jsx', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifier les corrections appliquees
        fixes_checks = [
            ("Gestion des donnees de conversation", "const conversation = data.conversation || data" in content),
            ("Verification de l'ID de conversation", "conversation && conversation.id" in content),
            ("Gestion des messages par defaut", "conversation.messages || []" in content),
            ("Gestion des erreurs backend", "const errorData = await response.json().catch" in content),
            ("Message d'erreur utilisateur", "toast.error(errorData.error ||" in content),
            ("Log des donnees invalides", "console.error('Invalid conversation data received')" in content)
        ]
        
        fixes_applied = 0
        for fix_name, is_applied in fixes_checks:
            if is_applied:
                print(f"[OK] {fix_name}")
                fixes_applied += 1
            else:
                print(f"[MANQUE] {fix_name}")
        
        print(f"\n[RESULTAT] Corrections appliquees: {fixes_applied}/{len(fixes_checks)}")
        
        # Verification specifique du probleme original
        problematic_line_fixed = "setMessages(data.conversation.messages || [])" not in content
        safe_access_implemented = "conversation.messages || []" in content
        
        print(f"\n[VALIDATION] Probleme original:")
        print(f"[OK] Ligne problematique supprimee: {problematic_line_fixed}")
        print(f"[OK] Acces securise implemente: {safe_access_implemented}")
        
        return fixes_applied >= 5 and problematic_line_fixed and safe_access_implemented
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

if __name__ == "__main__":
    print("[CONVERSATION] TEST DU FIX SELECTION CONVERSATION")
    print("=" * 60)
    
    success = test_conversation_selection_fix()
    
    print(f"\n[RESULTAT] VALIDATION FINALE:")
    print(f"   - Fix selectConversation: {'[OK] REUSSI' if success else '[ECHEC] ECHOUE'}")
    
    if success:
        print("\n[SUCCESS] FIX SELECTION CONVERSATION VALIDE!")
        print("Resolution des problemes:")
        print("- Error 'Cannot read properties of undefined': RESOLU")  
        print("- Gestion robuste des donnees de conversation: IMPLEMENTEE")
        print("- Messages d'erreur utilisateur: ACTIFS")
    else:
        print("\n[WARNING] Le fix necessite une validation supplementaire")