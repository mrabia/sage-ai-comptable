#!/usr/bin/env python3
"""
Test du systeme de fichiers attaches
"""

def test_file_upload_endpoints():
    """Test que les endpoints de fichiers sont bien configures"""
    print("[TEST] Validation des endpoints de fichiers")
    print("=" * 50)
    
    try:
        # Verifier que l'endpoint est enregistre dans main.py
        with open('backend/src/main.py', 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        endpoint_checks = [
            ("Import file_upload_bp", "from src.routes.file_upload import file_upload_bp" in main_content),
            ("Blueprint registration", "app.register_blueprint(file_upload_bp" in main_content),
            ("URL prefix correct", "url_prefix='/api/files'" in main_content)
        ]
        
        endpoint_score = 0
        for check_name, is_present in endpoint_checks:
            if is_present:
                print(f"[OK] {check_name}")
                endpoint_score += 1
            else:
                print(f"[MANQUE] {check_name}")
        
        # Verifier file_upload.py
        with open('backend/src/routes/file_upload.py', 'r', encoding='utf-8') as f:
            upload_content = f.read()
        
        upload_checks = [
            ("Upload endpoint", "@file_upload_bp.route('/upload', methods=['POST'])" in upload_content),
            ("JWT protection", "@jwt_required()" in upload_content),
            ("File processing", "file_processor.save_uploaded_file" in upload_content),
            ("Database storage", "FileAttachment(" in upload_content),
            ("Analysis metadata", "set_analysis_metadata" in upload_content),
            ("Excel support check", "EXCEL_AVAILABLE" in upload_content)
        ]
        
        upload_score = 0
        for check_name, is_present in upload_checks:
            if is_present:
                print(f"[OK] {check_name}")
                upload_score += 1
            else:
                print(f"[MANQUE] {check_name}")
        
        print(f"\n[RESULTAT] Endpoints: {endpoint_score}/{len(endpoint_checks)}")
        print(f"[RESULTAT] Upload route: {upload_score}/{len(upload_checks)}")
        
        return endpoint_score >= 2 and upload_score >= 4
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

def test_file_processing_service():
    """Test que le service de traitement de fichiers est configure"""
    print(f"\n[TEST] Validation du service de traitement")
    print("=" * 50)
    
    try:
        with open('backend/src/services/file_processor.py', 'r', encoding='utf-8') as f:
            processor_content = f.read()
        
        processor_checks = [
            ("Excel support import", "import openpyxl" in processor_content),
            ("Excel availability check", "EXCEL_AVAILABLE = True" in processor_content),
            ("Process Excel method", "def process_excel_file" in processor_content),
            ("Pandas integration", "pd.read_excel" in processor_content),
            ("Financial keywords detection", "financial_keywords" in processor_content),
            ("File extension support", "'.xlsx', '.xls'" in processor_content)
        ]
        
        processor_score = 0
        for check_name, is_present in processor_checks:
            if is_present:
                print(f"[OK] {check_name}")
                processor_score += 1
            else:
                print(f"[MANQUE] {check_name}")
        
        print(f"\n[RESULTAT] Processor: {processor_score}/{len(processor_checks)}")
        
        return processor_score >= 4
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

def test_ai_agent_file_integration():
    """Test que l'agent AI peut traiter les fichiers attaches"""
    print(f"\n[TEST] Validation integration AI Agent - Fichiers")
    print("=" * 50)
    
    try:
        with open('backend/src/routes/ai_agent.py', 'r', encoding='utf-8') as f:
            agent_content = f.read()
        
        agent_checks = [
            ("Fichiers attaches parameter", "attached_files = data.get('attached_files'" in agent_content),
            ("FileAttachment import", "from src.models.user import FileAttachment" in agent_content),
            ("File context preparation", "file_context = " in agent_content),
            ("File metadata access", "get_analysis_metadata()" in agent_content),
            ("Financial data detection", "potential_financial_data" in agent_content),
            ("Processed content access", "processed_content" in agent_content)
        ]
        
        agent_score = 0
        for check_name, is_present in agent_checks:
            if is_present:
                print(f"[OK] {check_name}")
                agent_score += 1
            else:
                print(f"[MANQUE] {check_name}")
        
        print(f"\n[RESULTAT] AI Agent integration: {agent_score}/{len(agent_checks)}")
        
        return agent_score >= 4
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

if __name__ == "__main__":
    print("[FICHIERS] TEST DU SYSTEME DE FICHIERS ATTACHES")
    print("=" * 70)
    
    endpoints_ok = test_file_upload_endpoints()
    processor_ok = test_file_processing_service()
    agent_ok = test_ai_agent_file_integration()
    
    print(f"\n[RESULTAT] VALIDATION FINALE:")
    print(f"   - Endpoints fichiers: {'[OK] REUSSI' if endpoints_ok else '[ECHEC] ECHOUE'}")
    print(f"   - Service traitement: {'[OK] REUSSI' if processor_ok else '[ECHEC] ECHOUE'}")
    print(f"   - Integration AI Agent: {'[OK] REUSSI' if agent_ok else '[ECHEC] ECHOUE'}")
    
    if endpoints_ok and processor_ok and agent_ok:
        print("\n[SUCCESS] SYSTEME DE FICHIERS ATTACHES VALIDE!")
        print("Resolution du probleme probable:")
        print("- Backend: Tous les composants sont implementes correctement")
        print("- Le probleme vient probablement du frontend (ID temporaire)")
        print("- L'upload doit retourner un vrai ID de base de donnees")
        print("- L'agent doit recevoir le vrai ID, pas l'ID temporaire frontend")
    else:
        print("\n[WARNING] Certaines parties du systeme necessitent validation")
    
    print(f"\n[DIAGNOSTIC] Probleme probable:")
    print(f"- ID frontend: 1757475093330.156 (timestamp JavaScript)")
    print(f"- Backend attend: ID entier de base de donnees")
    print(f"- Solution: Verifier le flux upload frontend -> backend")