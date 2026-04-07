"""
Monitor Redis queues to see if tasks are being received
"""
import redis
import json
import time

def monitor_redis_queues():
    """Monitor Redis to see tasks in the queues"""
    print("=" * 60)
    print("REDIS QUEUE MONITOR")
    print("=" * 60)
    
    try:
        # Connect to Redis broker (database 1)
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        print("\n✅ Connected to Redis (database 1 - Celery broker)")
        
        # Check all keys
        print("\n=== All Keys in Database 1 ===")
        keys = r.keys('*')
        if keys:
            for key in keys:
                key_type = r.type(key)
                print(f"  - {key} (type: {key_type})")
                
                # If it's a list, show its length
                if key_type == 'list':
                    length = r.llen(key)
                    print(f"    Length: {length}")
                    
                    # Show pending tasks in this queue
                    if length > 0:
                        print(f"    Pending items:")
                        items = r.lrange(key, 0, -1)
                        for i, item in enumerate(items[:5]):  # Show first 5
                            try:
                                data = json.loads(item)
                                print(f"      [{i+1}] Task: {data.get('headers', {}).get('task', 'unknown')}")
                                print(f"          ID: {data.get('headers', {}).get('id', 'unknown')}")
                            except:
                                print(f"      [{i+1}] {item[:100]}...")
        else:
            print("  No keys found")
        
        # Check for Celery default queue
        print("\n=== Checking Default Celery Queue ===")
        celery_queue = 'celery'
        queue_length = r.llen(celery_queue)
        print(f"Queue '{celery_queue}' length: {queue_length}")
        
        if queue_length > 0:
            print("\n⚠️  TASKS FOUND IN QUEUE BUT NOT BEING PROCESSED!")
            print("   This means the Celery worker is NOT consuming tasks.")
            print("\n   Possible issues:")
            print("   1. Worker command might be incorrect")
            print("   2. Worker might not be running")
            print("   3. Worker might be connected to wrong Redis database")
        else:
            print("\n✅ Queue is empty (tasks being processed or none queued)")
        
        # Check task results (database 2)
        print("\n=== Checking Results Backend (database 2) ===")
        r2 = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)
        result_keys = r2.keys('celery-task-meta-*')
        print(f"Found {len(result_keys)} task results")
        
    except redis.ConnectionError as e:
        print(f"\n❌ Cannot connect to Redis: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    monitor_redis_queues()
    
    print("\n" + "=" * 60)
    print("MONITORING (will check every 5 seconds)")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while True:
            time.sleep(5)
            print(f"\n--- Checking at {time.strftime('%H:%M:%S')} ---")
            r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            queue_length = r.llen('celery')
            print(f"'celery' queue length: {queue_length}")
            
            if queue_length > 0:
                print(f"⚠️  {queue_length} tasks waiting in queue!")
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
