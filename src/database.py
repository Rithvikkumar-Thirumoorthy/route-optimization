import pyodbc
import os
from dotenv import load_dotenv
import pandas as pd
import warnings
from sqlalchemy import create_engine, pool
from urllib.parse import quote_plus

load_dotenv()

# Suppress the pandas warning about DBAPI2 connections
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy connectable')

class DatabaseConnection:
    def __init__(self, pool_size=5, max_overflow=10):
        """
        Initialize database connection with connection pooling support

        Args:
            pool_size: Number of connections to keep in pool (default: 5)
            max_overflow: Max additional connections beyond pool_size (default: 10)
        """
        self.server = os.getenv('DB_SERVER')
        self.database = os.getenv('DB_DATABASE')
        self.use_windows_auth = os.getenv('DB_USE_WINDOWS_AUTH') == 'True'
        self.username = os.getenv('DB_USERNAME')
        self.password = os.getenv('DB_PASSWORD')
        self.connection = None
        self.engine = None
        self.pool_size = pool_size
        self.max_overflow = max_overflow

    def connect(self, enable_pooling=True):
        """
        Connect to database with optional connection pooling

        Args:
            enable_pooling: Use connection pooling for better performance (default: True)
        """
        try:
            # Create pyodbc connection with performance optimizations
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"MARS_Connection=yes;"  # Enable Multiple Active Result Sets
            )

            print(f"Connecting to: {self.server}, Database: {self.database}")
            self.connection = pyodbc.connect(connection_string, autocommit=False)

            # Set fast execution mode
            self.connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            self.connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            self.connection.setencoding(encoding='utf-8')

            # Create SQLAlchemy engine with connection pooling
            encoded_password = quote_plus(self.password)
            encoded_username = quote_plus(self.username)
            sqlalchemy_url = (
                f"mssql+pyodbc://{encoded_username}:{encoded_password}@{self.server}/"
                f"{self.database}?driver=ODBC+Driver+17+for+SQL+Server&"
                f"TrustServerCertificate=yes&MARS_Connection=yes"
            )

            if enable_pooling:
                # Create engine with connection pooling for better performance
                self.engine = create_engine(
                    sqlalchemy_url,
                    poolclass=pool.QueuePool,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_pre_ping=True,  # Verify connections before using
                    pool_recycle=3600,   # Recycle connections after 1 hour
                    echo=False
                )
            else:
                self.engine = create_engine(sqlalchemy_url)

            print(f"Database connection successful! (Pooling: {enable_pooling})")
            return self.connection
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

    def execute_query(self, query, params=None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    def execute_query_df(self, query, params=None):
        try:
            # Use SQLAlchemy engine for pandas to avoid warnings
            if self.engine:
                if params:
                    return pd.read_sql(query, self.engine, params=params)
                else:
                    return pd.read_sql(query, self.engine)
            else:
                # Fallback to pyodbc connection with warning suppression
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if params:
                        return pd.read_sql(query, self.connection, params=params)
                    else:
                        return pd.read_sql(query, self.connection)
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    def execute_insert(self, query, params):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error executing insert: {e}")
            return False

    def execute_bulk_insert(self, query, data_list):
        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, data_list)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error executing bulk insert: {e}")
            return False

    def close(self):
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()