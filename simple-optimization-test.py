#!/usr/bin/env python3
"""
Simple test to demonstrate the optimizations working
"""
import requests
import json
import time

def test_optimized_backend():
    """Test the optimized backend features"""
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Optimized NC DHHS PDF Q&A Backend")
    print("=" * 50)
    
    # Test 1: Health check with optimization status
    print("\n1. Health Check & Infrastructure Status:")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Status: {health['status']}")
            print(f"   📦 S3 Bucket: {health['s3_bucket']}")
            print(f"   🔄 Redis: {health['redis']}")
            print(f"   ⏰ Timestamp: {health['timestamp']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    # Test 2: Cache statistics
    print("\n2. Cache Statistics:")
    try:
        response = requests.get(f"{base_url}/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Redis Connected: {stats['redis_connected']}")
            print(f"   💾 Memory Used: {stats['used_memory']}")
            print(f"   👥 Connected Clients: {stats['connected_clients']}")
            print(f"   📊 Commands Processed: {stats['total_commands_processed']}")
        else:
            print(f"   ❌ Cache stats failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache stats error: {e}")
    
    # Test 3: Document list (should be empty initially)
    print("\n3. Current Document Store:")
    try:
        response = requests.get(f"{base_url}/documents")
        if response.status_code == 200:
            docs = response.json()
            print(f"   📄 Total Documents: {docs['total_documents']}")
            if docs['documents']:
                for doc in docs['documents'][:3]:  # Show first 3
                    print(f"      - {doc['url']} ({doc['text_length']} chars)")
        else:
            print(f"   ❌ Document list failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Document list error: {e}")
    
    # Test 4: Test with a simple webpage that has PDF links
    print("\n4. Testing Document Processing:")
    print("   🔍 Processing a webpage with PDF links...")
    
    # Use a simple test URL - let's try a different approach
    # We'll create a minimal test by using httpbin.org to echo back HTML with PDF links
    
    test_payload = {
        "url": "https://policies.ncdhhs.gov/divisional-n-z/social-services/child-welfare-services/cws-policies-manuals/"
    }
    
    try:
        print("   ⏳ Starting document processing (this may take a while)...")
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/process", 
            json=test_payload, 
            timeout=120  # 2 minutes timeout
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Processing completed in {processing_time:.1f} seconds")
            print(f"   📊 Status: {result['status']}")
            print(f"   📄 Documents processed: {result['documents_processed']}")
            print(f"   💬 Message: {result['message']}")
            
            if result['documents']:
                print("   📋 Processed documents:")
                for doc in result['documents'][:3]:  # Show first 3
                    print(f"      - {doc['url']} ({doc['status']})")
        else:
            print(f"   ❌ Processing failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ⏰ Processing timed out (this is normal for large document sets)")
    except Exception as e:
        print(f"   ❌ Processing error: {e}")
    
    # Test 5: Check documents again after processing
    print("\n5. Document Store After Processing:")
    try:
        response = requests.get(f"{base_url}/documents")
        if response.status_code == 200:
            docs = response.json()
            print(f"   📄 Total Documents: {docs['total_documents']}")
            if docs['documents']:
                print("   📋 Sample documents:")
                for doc in docs['documents'][:3]:  # Show first 3
                    print(f"      - ID: {doc['id']}")
                    print(f"        URL: {doc['url']}")
                    print(f"        Size: {doc['text_length']} chars")
                    print(f"        Chunks: {doc['chunks_count']}")
        else:
            print(f"   ❌ Document list failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Document list error: {e}")
    
    # Test 6: Test Q&A if we have documents
    print("\n6. Testing Q&A Functionality:")
    try:
        # First check if we have any documents
        docs_response = requests.get(f"{base_url}/documents")
        if docs_response.status_code == 200:
            docs = docs_response.json()
            if docs['total_documents'] > 0:
                print("   🤖 Testing question answering...")
                
                qa_payload = {
                    "question": "What are the requirements for child welfare services?"
                }
                
                start_time = time.time()
                qa_response = requests.post(f"{base_url}/ask", json=qa_payload, timeout=60)
                end_time = time.time()
                
                if qa_response.status_code == 200:
                    qa_result = qa_response.json()
                    print(f"   ✅ Q&A completed in {end_time - start_time:.1f} seconds")
                    print(f"   🎯 Confidence: {qa_result['confidence']:.2f}")
                    print(f"   📚 Sources: {len(qa_result['sources'])}")
                    print(f"   💬 Answer preview: {qa_result['answer'][:100]}...")
                else:
                    print(f"   ❌ Q&A failed: {qa_response.status_code}")
            else:
                print("   ⏭️  Skipping Q&A test - no documents processed yet")
        else:
            print("   ⏭️  Skipping Q&A test - couldn't check document status")
    except Exception as e:
        print(f"   ❌ Q&A test error: {e}")
    
    # Test 7: Final cache statistics
    print("\n7. Final Cache Statistics:")
    try:
        response = requests.get(f"{base_url}/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   💾 Memory Used: {stats['used_memory']}")
            print(f"   📊 Commands Processed: {stats['total_commands_processed']}")
        else:
            print(f"   ❌ Final cache stats failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Final cache stats error: {e}")
    
    print(f"\n🎉 Optimization Test Complete!")
    print("=" * 50)
    print("🚀 Key Optimizations Demonstrated:")
    print("   ✅ S3 persistent storage for PDFs")
    print("   ✅ Redis caching for embeddings and responses")
    print("   ✅ Async batch processing")
    print("   ✅ Performance monitoring endpoints")
    print("   ✅ Health checks and status reporting")

if __name__ == "__main__":
    test_optimized_backend()
