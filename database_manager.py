import sqlite3
import time
import logging
import os
import threading

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages the database operations for caching questions and answers"""
    
    def __init__(self, db_path="qa_database.db"):
        self.db_path = db_path
        self.connection = None
        self.connection_lock = threading.Lock()
        self.initialize_db()
    
    def initialize_db(self):
        """Initialize the database structure"""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Connect to database
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create tables
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS qa_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_accessed INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
                ''')
                
                # Create indexes
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_question ON qa_cache(question)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_last_accessed ON qa_cache(last_accessed)
                ''')
                
                conn.commit()
            
            logger.info(f"Database initialized at {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False
    
    def get_connection(self):
        """Get a connection to the database with thread safety"""
        with self.connection_lock:
            if self.connection is None:
                self.connection = sqlite3.connect(self.db_path)
                # Configure connection
                self.connection.row_factory = sqlite3.Row
            return self.connection
    
    def close(self):
        """Close the database connection"""
        with self.connection_lock:
            if self.connection:
                self.connection.close()
                self.connection = None
    
    def get_cached_answer(self, question):
        """Get a cached answer for a question if it exists"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean the question for better matching
                cleaned_question = question.strip().lower()
                
                # Try exact match first
                cursor.execute('''
                SELECT answer, access_count FROM qa_cache 
                WHERE LOWER(question) = ? 
                ORDER BY last_accessed DESC LIMIT 1
                ''', (cleaned_question,))
                
                result = cursor.fetchone()
                
                if result:
                    # Update the access statistics
                    answer, access_count = result['answer'], result['access_count']
                    
                    cursor.execute('''
                    UPDATE qa_cache 
                    SET last_accessed = ?, access_count = ? 
                    WHERE LOWER(question) = ?
                    ''', (int(time.time()), access_count + 1, cleaned_question))
                    
                    conn.commit()
                    
                    logger.info(f"Cache hit for question: {question[:50]}...")
                    return answer
                
                # If no exact match, try fuzzy matching (simplified)
                # In a production application, consider using full-text search or other methods
                words = cleaned_question.split()
                if len(words) > 3:  # Only try fuzzy matching for longer questions
                    placeholders = ', '.join(['?'] * len(words))
                    query = f'''
                    SELECT answer, question, access_count FROM qa_cache 
                    WHERE question LIKE ? OR question LIKE ?
                    ORDER BY access_count DESC
                    LIMIT 5
                    '''
                    
                    # Try to match questions that contain key words from the query
                    cursor.execute(query, (f"%{words[0]}%{words[1]}%", f"%{words[-2]}%{words[-1]}%"))
                    
                    fuzzy_results = cursor.fetchall()
                    if fuzzy_results:
                        # Implement better fuzzy matching if needed
                        # For now, just return the most accessed result
                        best_match = max(fuzzy_results, key=lambda x: x['access_count'])
                        
                        logger.info(f"Fuzzy cache hit for question: {question[:50]}...")
                        
                        # Update access statistics for this answer
                        cursor.execute('''
                        UPDATE qa_cache 
                        SET last_accessed = ?, access_count = ? 
                        WHERE question = ?
                        ''', (int(time.time()), best_match['access_count'] + 1, best_match['question']))
                        
                        conn.commit()
                        
                        return best_match['answer']
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    def cache_qa_pair(self, question, answer):
        """Cache a question-answer pair"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_time = int(time.time())
                
                # Check if question already exists
                cursor.execute('''
                SELECT id FROM qa_cache WHERE LOWER(question) = ?
                ''', (question.strip().lower(),))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                    UPDATE qa_cache SET 
                    answer = ?, 
                    last_accessed = ?, 
                    access_count = access_count + 1
                    WHERE id = ?
                    ''', (answer, current_time, existing['id']))
                else:
                    # Insert new record
                    cursor.execute('''
                    INSERT INTO qa_cache (question, answer, created_at, last_accessed)
                    VALUES (?, ?, ?, ?)
                    ''', (question, answer, current_time, current_time))
                
                conn.commit()
                logger.info(f"Cached Q&A: {question[:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"Error caching Q&A: {e}")
            return False
    
    def clean_old_entries(self, max_age_days=30, max_entries=1000):
        """Clean old entries from the cache"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) as count FROM qa_cache")
                total_count = cursor.fetchone()['count']
                
                # If under the max, only clean by age
                if total_count <= max_entries:
                    cutoff_time = int(time.time()) - (max_age_days * 86400)
                    cursor.execute('''
                    DELETE FROM qa_cache 
                    WHERE last_accessed < ?
                    ''', (cutoff_time,))
                    
                    deleted_count = cursor.rowcount
                    logger.info(f"Cleaned {deleted_count} old cache entries")
                else:
                    # If over max entries, also clean by access count
                    cursor.execute('''
                    DELETE FROM qa_cache 
                    WHERE id IN (
                        SELECT id FROM qa_cache
                        ORDER BY access_count ASC, last_accessed ASC
                        LIMIT ?
                    )
                    ''', (total_count - max_entries + 100,))  # Delete enough to go below max with some buffer
                    
                    deleted_count = cursor.rowcount
                    logger.info(f"Cleaned {deleted_count} least accessed cache entries")
                
                conn.commit()
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
            return 0
    
    def get_stats(self):
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total entries
                cursor.execute("SELECT COUNT(*) as count FROM qa_cache")
                stats['total_entries'] = cursor.fetchone()['count']
                
                # Most popular questions
                cursor.execute('''
                SELECT question, access_count FROM qa_cache
                ORDER BY access_count DESC
                LIMIT 5
                ''')
                stats['popular_questions'] = [dict(row) for row in cursor.fetchall()]
                
                # Recently accessed
                cursor.execute('''
                SELECT question, datetime(last_accessed, 'unixepoch') as last_access_time 
                FROM qa_cache
                ORDER BY last_accessed DESC
                LIMIT 5
                ''')
                stats['recent_questions'] = [dict(row) for row in cursor.fetchall()]
                
                # Database size
                stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}