"""
MongoDB Atlas Connection Test Script
=====================================

This script tests your MongoDB Atlas connection and verifies everything is working.

Usage:
    python test_mongodb_connection.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Load environment variables
load_env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(load_env_path)

def test_connection():
    """Test MongoDB Atlas connection"""
    
    print("=" * 60)
    print("🔌 MongoDB Atlas Connection Test")
    print("=" * 60)
    print()
    
    # Get connection string from .env
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'bankstatement_saas')
    
    if not mongodb_uri:
        print("❌ ERROR: MONGODB_URI not found in .env file!")
        print()
        print("Please add your MongoDB Atlas connection string to .env:")
        print("MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/")
        print()
        return False
    
    # Check if still using placeholder
    if 'username:password' in mongodb_uri or 'xxxxx' in mongodb_uri:
        print("⚠️  WARNING: You're still using the placeholder connection string!")
        print()
        print("Please replace with your actual MongoDB Atlas connection string:")
        print("1. Go to MongoDB Atlas dashboard")
        print("2. Click 'Connect' on your cluster")
        print("3. Choose 'Connect your application'")
        print("4. Copy the connection string")
        print("5. Update MONGODB_URI in .env file")
        print()
        return False
    
    print(f"📝 Database: {database_name}")
    print(f"🔗 Connection URI: {mongodb_uri[:30]}...{mongodb_uri[-20:]}")
    print()
    
    try:
        # Create MongoDB client
        print("🔄 Connecting to MongoDB Atlas...")
        client = MongoClient(
            mongodb_uri,
            server_api=ServerApi('1'),
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        print("✅ Connection established!")
        print()
        
        # Get database
        db = client[database_name]
        
        # Test database access
        print("🔄 Testing database operations...")
        
        # 1. Create a test collection
        test_collection = db['connection_test']
        
        # 2. Insert a test document
        test_doc = {
            'test': 'connection',
            'timestamp': datetime.utcnow(),
            'message': 'MongoDB Atlas connection successful!'
        }
        result = test_collection.insert_one(test_doc)
        print(f"✅ Inserted test document with ID: {result.inserted_id}")
        
        # 3. Read the document back
        found_doc = test_collection.find_one({'_id': result.inserted_id})
        print(f"✅ Retrieved test document: {found_doc['message']}")
        
        # 4. Update the document
        test_collection.update_one(
            {'_id': result.inserted_id},
            {'$set': {'updated': True}}
        )
        print("✅ Updated test document")
        
        # 5. Delete the document
        test_collection.delete_one({'_id': result.inserted_id})
        print("✅ Deleted test document")
        
        # Get server info
        print()
        print("📊 Server Information:")
        server_info = client.server_info()
        print(f"   - MongoDB Version: {server_info['version']}")
        print(f"   - Server: {server_info.get('host', 'Atlas Cluster')}")
        
        # List collections
        print()
        print("📁 Existing Collections:")
        collections = db.list_collection_names()
        if collections:
            for collection in collections:
                count = db[collection].count_documents({})
                print(f"   - {collection}: {count} documents")
        else:
            print("   (No collections yet)")
        
        # Get database stats
        print()
        print("💾 Database Statistics:")
        stats = db.command('dbstats')
        print(f"   - Size: {stats.get('dataSize', 0) / 1024:.2f} KB")
        print(f"   - Collections: {stats.get('collections', 0)}")
        print(f"   - Indexes: {stats.get('indexes', 0)}")
        
        print()
        print("=" * 60)
        print("✅ MongoDB Atlas Connection Test PASSED!")
        print("=" * 60)
        print()
        print("🎉 Your database is ready to use!")
        print()
        print("Next steps:")
        print("1. Run: python app_azure.py")
        print("2. Visit: http://localhost:8000")
        print("3. Upload a PDF to test the full flow")
        print()
        
        client.close()
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ MongoDB Atlas Connection Test FAILED!")
        print("=" * 60)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print()
        print("1. Wrong connection string:")
        print("   - Check username and password")
        print("   - Ensure no special characters in password (or URL encode them)")
        print()
        print("2. Network access not configured:")
        print("   - Go to MongoDB Atlas → Network Access")
        print("   - Add your IP address or allow 0.0.0.0/0 (Allow from anywhere)")
        print()
        print("3. Database user not created:")
        print("   - Go to MongoDB Atlas → Database Access")
        print("   - Create a new database user with password")
        print()
        print("4. Connection timeout:")
        print("   - Check your internet connection")
        print("   - Try again in a few seconds")
        print()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
