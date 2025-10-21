"""Test MongoDB integration"""
from database import db
from models_mongodb import User, Conversion

print('✅ MongoDB models imported!')
print(f'✅ Database: {db.name}')

# Get stats
stats = Conversion.get_stats()
print(f'✅ Total conversions: {stats["total_conversions"]}')
print(f'✅ Total pages: {stats["total_pages"]}')

# Test user operations
print('\n🔄 Testing user operations...')
user = User.create_or_get('test_user_123', 'free')
print(f'✅ User created: {user["user_id"]}')

usage = User.get_usage('test_user_123')
print(f'✅ Usage retrieved: {usage["pages_used"]} pages used')

print('\n🎉 MongoDB integration working perfectly!')
