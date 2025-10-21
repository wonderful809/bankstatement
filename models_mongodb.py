"""
MongoDB Data Models
===================

Data models and helper functions for MongoDB collections.
"""

from datetime import datetime, timedelta
from database import users_collection, conversions_collection


class User:
    """User session model"""
    
    @staticmethod
    def create_or_get(user_id, plan='free'):
        """Create new user or get existing"""
        
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            user = {
                'user_id': user_id,
                'plan': plan,
                'pages_used': 0,
                'last_reset': datetime.utcnow(),
                'created_at': datetime.utcnow(),
                'last_activity': datetime.utcnow()
            }
            users_collection.insert_one(user)
        else:
            # Update last activity
            users_collection.update_one(
                {'user_id': user_id},
                {'$set': {'last_activity': datetime.utcnow()}}
            )
        
        return user
    
    @staticmethod
    def get_usage(user_id):
        """Get user's current usage"""
        
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            return {
                'pages_used': 0,
                'plan': 'free',
                'last_reset': datetime.utcnow()
            }
        
        # Check if monthly reset is needed
        last_reset = user.get('last_reset', datetime.utcnow())
        if (datetime.utcnow() - last_reset).days >= 30:
            # Reset monthly usage
            users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'pages_used': 0,
                        'last_reset': datetime.utcnow()
                    }
                }
            )
            return {
                'pages_used': 0,
                'plan': user.get('plan', 'free'),
                'last_reset': datetime.utcnow()
            }
        
        return {
            'pages_used': user.get('pages_used', 0),
            'plan': user.get('plan', 'free'),
            'last_reset': user.get('last_reset', datetime.utcnow())
        }
    
    @staticmethod
    def update_usage(user_id, pages):
        """Update user's page usage"""
        
        result = users_collection.update_one(
            {'user_id': user_id},
            {
                '$inc': {'pages_used': pages},
                '$set': {'last_activity': datetime.utcnow()}
            },
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def get_plan_limits(plan):
        """Get page limits for plan"""
        
        limits = {
            'free': 5,
            'starter': 100,
            'professional': 500,
            'business': float('inf')
        }
        
        return limits.get(plan, 5)
    
    @staticmethod
    def can_convert(user_id, pages):
        """Check if user can convert given number of pages"""
        
        usage = User.get_usage(user_id)
        plan = usage['plan']
        pages_used = usage['pages_used']
        limit = User.get_plan_limits(plan)
        
        return pages_used + pages <= limit


class Conversion:
    """Conversion record model"""
    
    @staticmethod
    def create(user_id, filename, pages, transactions, status='success', processing_time=0):
        """Create new conversion record"""
        
        conversion = {
            'user_id': user_id,
            'filename': filename,
            'pages': pages,
            'transactions': transactions,
            'status': status,
            'processing_time': processing_time,
            'created_at': datetime.utcnow(),
            'expireAt': datetime.utcnow() + timedelta(hours=1)  # Auto-delete after 1 hour
        }
        
        result = conversions_collection.insert_one(conversion)
        return str(result.inserted_id)
    
    @staticmethod
    def get_user_history(user_id, limit=20):
        """Get user's conversion history"""
        
        conversions = conversions_collection.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(limit)
        
        return list(conversions)
    
    @staticmethod
    def get_stats():
        """Get overall conversion statistics"""
        
        total_conversions = conversions_collection.count_documents({})
        
        # Get successful conversions
        successful = conversions_collection.count_documents({'status': 'success'})
        
        # Get total pages processed
        pipeline = [
            {'$group': {
                '_id': None,
                'total_pages': {'$sum': '$pages'},
                'total_transactions': {'$sum': '$transactions'},
                'avg_time': {'$avg': '$processing_time'}
            }}
        ]
        
        stats = list(conversions_collection.aggregate(pipeline))
        
        if stats:
            return {
                'total_conversions': total_conversions,
                'successful_conversions': successful,
                'total_pages': stats[0].get('total_pages', 0),
                'total_transactions': stats[0].get('total_transactions', 0),
                'avg_processing_time': round(stats[0].get('avg_time', 0), 2)
            }
        else:
            return {
                'total_conversions': 0,
                'successful_conversions': 0,
                'total_pages': 0,
                'total_transactions': 0,
                'avg_processing_time': 0
            }
