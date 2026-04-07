"""
Test script to verify Celery and Redis connectivity
"""
import socket
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_redis_connection():
    """Test if Redis is accessible"""
    print("\n=== Testing Redis Connection ===")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()
        
        if result == 0:
            print("✅ Redis is reachable at localhost:6379")
            return True
        else:
            print(f"❌ Redis connection failed with code: {result}")
            return False
    except Exception as e:
        print(f"❌ Error checking Redis: {e}")
        return False


def test_celery_import():
    """Test if Celery app and tasks can be imported"""
    print("\n=== Testing Celery Imports ===")
    try:
        from app.workers.processor import celery, process_document
        print("✅ Successfully imported Celery app")
        print(f"   Broker: {celery.conf.broker_url}")
        print(f"   Backend: {celery.conf.result_backend}")
        print("✅ Successfully imported process_document task")
        print(f"   Task name: {process_document.name}")
        return True, celery, process_document
    except Exception as e:
        print(f"❌ Failed to import Celery: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_task_enqueueing(process_document):
    """Test if we can enqueue a task"""
    print("\n=== Testing Task Enqueueing ===")
    try:
        # Try to enqueue a dummy task
        print("Attempting to enqueue a test task...")
        task = process_document.delay(
            doc_path="./test.txt",
            doc_id="test-123",
            provider_name=None,
            enable_deduction=False,
            enable_patterns=False
        )
        print(f"✅ Task enqueued successfully!")
        print(f"   Task ID: {task.id}")
        print(f"   Task State: {task.state}")
        return True
    except Exception as e:
        print(f"❌ Failed to enqueue task: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enqueue_function():
    """Test the enqueue_document function directly"""
    print("\n=== Testing enqueue_document Function ===")
    try:
        from app.workers.tasks import enqueue_document
        print("✅ Successfully imported enqueue_document")
        
        # Test enqueueing
        print("Testing enqueue_document with dummy data...")
        task_id = enqueue_document(
            doc_path="./test.txt",
            doc_id="test-456",
            provider_name=None,
            enable_deduction=False,
            enable_patterns=False
        )
        print(f"✅ enqueue_document returned task ID: {task_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to test enqueue_document: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("CELERY & REDIS DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Test 1: Redis connection
    redis_ok = test_redis_connection()
    
    # Test 2: Celery imports
    celery_ok, celery_app, process_doc_task = test_celery_import()
    
    if celery_ok and process_doc_task:
        # Test 3: Direct task enqueueing
        task_ok = test_task_enqueueing(process_doc_task)
        
        # Test 4: enqueue_document function
        enqueue_ok = test_enqueue_function()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Redis Connection:    {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"Celery Import:       {'✅ PASS' if celery_ok else '❌ FAIL'}")
    if celery_ok:
        print(f"Task Enqueueing:     {'✅ PASS' if task_ok else '❌ FAIL'}")
        print(f"enqueue_document:    {'✅ PASS' if enqueue_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if redis_ok and celery_ok:
        print("\n📋 NEXT STEPS:")
        print("1. Check Celery worker terminal for incoming tasks")
        print("2. Tasks should appear in Celery worker logs")
        print("3. If tasks appear in logs, the setup is working!")
    else:
        print("\n⚠️  ISSUES DETECTED - Fix the above errors first")
