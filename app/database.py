"""
This module provides the AzureSQLReadOnlyConnection class which handles database connections
to Azure SQL Database and enforces read-only query safety. It validates queries to prevent
any write operations and provides a secure interface for executing read-only database operations.
"""

import os
import pyodbc
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

class AzureSQLReadOnlyConnection:
    def __init__(self):
        load_dotenv()
        
        self.server = os.getenv('DB_SERVER')
        self.database = os.getenv('DB_DATABASE')
        self.username = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        
        if not all([self.server, self.database, self.username, self.password]):
            raise ValueError("Missing required database environment variables: DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD")
        
        self.connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        self.connection: Optional[pyodbc.Connection] = None
    
    def connect(self) -> bool:
        """Establish connection to Azure SQL Database"""
        try:
            self.connection = pyodbc.connect(self.connection_string)
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def _is_read_only_query(self, query: str) -> bool:
        """Check if the query is strictly read-only"""
        clean_query = re.sub(r'--.*', '', query)  # Remove line comments
        clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)  # Remove block comments
        clean_query = re.sub(r'\s+', ' ', clean_query.strip().upper())
        
        write_patterns = [
            r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b', r'\bCREATE\b',
            r'\bALTER\b', r'\bTRUNCATE\b', r'\bMERGE\b', r'\bREPLACE\b',
            r'\bEXEC\b', r'\bEXECUTE\b', r'\bCALL\b', r'\bSP_\w+\b',
            r'\bBULK\s+INSERT\b', r'\bINTO\b.*\bVALUES\b'
        ]
        
        for pattern in write_patterns:
            if re.search(pattern, clean_query):
                return False
        
        allowed_patterns = [
            r'^\s*SELECT\b',
            r'^\s*;?\s*WITH\b.*\bSELECT\b',  # CTE with SELECT (with optional semicolon)
            r'^\s*DECLARE\b.*\bSELECT\b',  # Variable declarations followed by SELECT
            r'^\s*SHOW\b',
            r'^\s*DESCRIBE\b',
            r'^\s*EXPLAIN\b'
        ]
        
        for pattern in allowed_patterns:
            if re.search(pattern, clean_query, flags=re.DOTALL):
                return True
        
        return False
    
    def _serialize_for_json(self, obj):
        """Convert database values to JSON-serializable format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif obj is None:
            return None
        else:
            return str(obj)

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a read-only SELECT query and return results as list of dictionaries"""
        if not self._is_read_only_query(query):
            raise ValueError("Only read-only SELECT queries are allowed. Write operations are forbidden.")

        if not self.connection:
            if not self.connect():
                raise Exception("Failed to connect to database")

        assert self.connection is not None, "Connection should be established"
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description]

            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))

            cursor.close()
            return result

        except Exception as e:
            print(f"Error executing query: {e}")
            raise

    def execute_query_for_llm(self, query: str, params: Optional[tuple] = None) -> tuple[List[Dict[str, Any]], List[str]]:
        """Execute query and return both serialized results for logging and JSON strings for LLM processing"""
        db_results = self.execute_query(query, params)
        
        safe_results = []
        llm_results = []
        
        for row in db_results:
            serializable_row = {key: self._serialize_for_json(value) for key, value in row.items()}
            safe_results.append(serializable_row)
            llm_results.append(json.dumps(serializable_row, ensure_ascii=False))
        
        return safe_results, llm_results
    

    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

db = AzureSQLReadOnlyConnection() 