"""
MongoDB Database Connection Manager
====================================

Handles MongoDB Atlas connection, connection pooling, and error handling.
"""

import os
import ssl
import certifi
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MongoDB:
    """MongoDB connection manager with connection pooling"""
    
    _client = None
    _db = None
    
    @classmethod
    def get_client(cls):
        """Get MongoDB client (singleton pattern)"""
        if cls._client is None:
            mongodb_uri = os.environ.get('MONGODB_URI')
            
            if not mongodb_uri:
                raise ValueError("MONGODB_URI not found in environment variables")
            
            try:
                # Use same connection approach as test script (which worked)
                cls._client = MongoClient(
                    mongodb_uri,
                    server_api=ServerApi('1'),
                    serverSelectionTimeoutMS=5000
                )
                
                # Test connection
                cls._client.admin.command('ping')
                print("✅ MongoDB Atlas connected successfully")
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                print(f"❌ MongoDB connection failed: {str(e)}")
                raise
        
        return cls._client
    
    @classmethod
    def get_database(cls):
        """Get database instance"""
        if cls._db is None:
            client = cls.get_client()
            db_name = os.environ.get('MONGODB_DATABASE', 'bankstatement_saas')
            cls._db = client[db_name]
            print(f"✅ Using database: {db_name}")
        
        return cls._db
    
    @classmethod
    def close(cls):
        """Close MongoDB connection"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            print("✅ MongoDB connection closed")


# Database instance (singleton)
db = MongoDB.get_database()

# Collections
users_collection = db['users']
conversions_collection = db['conversions']


def init_indexes():
    """Initialize database indexes for performance"""
    
    print("🔄 Creating database indexes...")
    
    try:
        # Users collection indexes
        users_collection.create_index("user_id", unique=True)
        users_collection.create_index("last_activity")
        users_collection.create_index("plan")
        
        # Conversions collection indexes
        conversions_collection.create_index([("user_id", 1), ("created_at", -1)])
        conversions_collection.create_index("created_at")
        conversions_collection.create_index("status")
        
        # TTL index for auto-deletion (expires after 1 hour)
        conversions_collection.create_index(
            "expireAt",
            expireAfterSeconds=0
        )
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️  Index creation warning: {str(e)}")


# Initialize indexes on module import
try:
    init_indexes()
except Exception as e:
    print(f"⚠️  Could not initialize indexes: {str(e)}")
