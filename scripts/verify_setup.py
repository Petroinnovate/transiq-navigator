"""
Setup Verification Script for TransIQ Backend
Tests all components and provides setup status
"""

import sys
import os
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_mark(condition):
    return "✓" if condition else "✗"

def main():
    print("\n" + "="*60)
    print("  TransIQ Backend - Setup Verification")
    print("="*60)
    
    all_checks_passed = True
    
    # 1. Check Python packages
    print_section("1. Python Packages")
    
    required_packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'sentence_transformers': 'Sentence Transformers',
        'numpy': 'NumPy',
        'supabase': 'Supabase',
        'google.genai': 'Google Gemini',
        'pandas': 'Pandas',
        'fitz': 'PyMuPDF',
        'python-dotenv': 'Python Dotenv'
    }
    
    for package, name in required_packages.items():
        try:
            if package == 'python-dotenv':
                import dotenv
            elif package == 'google.genai':
                from google import genai
            else:
                __import__(package)
            print(f"  {check_mark(True)} {name:<25} - Installed")
        except ImportError:
            print(f"  {check_mark(False)} {name:<25} - NOT INSTALLED")
            all_checks_passed = False
    
    # 2. Check environment variables
    print_section("2. Environment Configuration")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = {
        'SUPABASE_URL': 'Supabase URL',
        'SUPABASE_ANON_KEY': 'Supabase Anon Key',
        'GEMINI_API_KEY': 'Gemini API Key'
    }
    
    env_file_exists = Path('.env').exists()
    print(f"  {check_mark(env_file_exists)} .env file exists")
    
    if not env_file_exists:
        print("    → Create .env file with your credentials")
        all_checks_passed = False
    
    for var, name in env_vars.items():
        value = os.getenv(var)
        is_set = value is not None and value != "" and not value.startswith("your-")
        print(f"  {check_mark(is_set)} {name:<25} - {'Set' if is_set else 'NOT SET'}")
        if not is_set:
            all_checks_passed = False
    
    # 3. Check vector storage
    print_section("3. Vector Storage Service")
    
    try:
        from services.vector_store.indexing.vector_storage import get_vector_service
        service = get_vector_service()
        print(f"  {check_mark(True)} Vector service initialized")
        print(f"    Model: {service.model_name}")
        print(f"    Embedding dimension: {service.embedding_dimension}")
        
        # Test embedding generation
        test_text = "Test embedding generation"
        embedding = service.generate_embedding(test_text)
        print(f"  {check_mark(len(embedding) == 384)} Embedding generation working")
        
    except Exception as e:
        print(f"  {check_mark(False)} Vector service - ERROR")
        print(f"    Error: {str(e)}")
        all_checks_passed = False
    
    # 4. Check Supabase connection
    print_section("4. Supabase Connection")
    
    try:
        from services.supabase.supabase_service import supabase_service
        
        has_client = supabase_service.client is not None
        print(f"  {check_mark(has_client)} Supabase client initialized")
        
        if has_client:
            print(f"    URL: {supabase_service.supabase_url[:30]}...")
            print(f"    Key: {supabase_service.supabase_key[:20]}...")
        else:
            print("    → Configure SUPABASE_URL and SUPABASE_ANON_KEY in .env")
            all_checks_passed = False
            
    except Exception as e:
        print(f"  {check_mark(False)} Supabase - ERROR")
        print(f"    Error: {str(e)}")
        all_checks_passed = False
    
    # 5. Check database schema
    print_section("5. Database Schema")
    
    schema_file = Path('supabase_schema.sql')
    print(f"  {check_mark(schema_file.exists())} Schema file exists: supabase_schema.sql")
    
    if schema_file.exists():
        print("\n  To set up the database:")
        print("  1. Go to Supabase Dashboard → SQL Editor")
        print("  2. Copy and run the contents of supabase_schema.sql")
        print("  3. Verify tables: documents, document_chunks")
        print("  4. Verify pgvector extension is enabled")
    
    # 6. Check required files
    print_section("6. Required Files")
    
    required_files = [
        'main.py',
        'llm.py',
        'chunker.py',
        'supabase_service.py',
        'vector_storage.py',
        'supa.py',
        'requirements.txt',
        'supabase_schema.sql',
        'VECTOR_STORAGE_SETUP.md'
    ]
    
    for file in required_files:
        exists = Path(file).exists()
        print(f"  {check_mark(exists)} {file}")
        if not exists:
            all_checks_passed = False
    
    # 7. Test imports
    print_section("7. Module Imports")
    
    modules = [
        ('main', 'main.py'),
        ('llm', 'llm.py'),
        ('chunker', 'chunker.py'),
        ('supabase_service', 'supabase_service.py'),
        ('vector_storage', 'vector_storage.py'),
        ('supa', 'supa.py')
    ]
    
    for module_name, file_name in modules:
        try:
            __import__(module_name)
            print(f"  {check_mark(True)} {file_name:<30} - OK")
        except Exception as e:
            print(f"  {check_mark(False)} {file_name:<30} - ERROR")
            print(f"    {str(e)[:60]}")
            all_checks_passed = False
    
    # Summary
    print_section("Summary")
    
    if all_checks_passed:
        print("\n  ✓ All checks passed!")
        print("\n  Next steps:")
        print("  1. Ensure Supabase database schema is set up")
        print("  2. Start the backend: python main.py")
        print("  3. Visit http://localhost:8001/docs")
        print("  4. Test document upload and search endpoints")
        return 0
    else:
        print("\n  ✗ Some checks failed. Please review the errors above.")
        print("\n  Common fixes:")
        print("  • Install missing packages: pip install -r requirements.txt")
        print("  • Configure .env file with your credentials")
        print("  • Run supabase_schema.sql in Supabase Dashboard")
        return 1

if __name__ == "__main__":
    sys.exit(main())
