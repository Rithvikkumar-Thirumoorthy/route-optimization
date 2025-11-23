import pyodbc
import os
from dotenv import load_dotenv
import pandas as pd
import warnings
from sqlalchemy import create_engine
from urllib.parse import quote_plus

load_dotenv()

# Suppress the pandas warning about DBAPI2 connections
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy connectable')

class DatabaseConnection:
    def __init__(self):
        self.server = os.getenv('DB_SERVER')
        self.database = os.getenv('DB_DATABASE')
        self.use_windows_auth = os.getenv('DB_USE_WINDOWS_AUTH') == 'True'
        self.username = os.getenv('DB_USERNAME')
        self.password = os.getenv('DB_PASSWORD')
        self.connection = None
        self.engine = None

    def connect(self):
        try:
            # Create pyodbc connection
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};"

            print(f"Connecting to: {self.server}, Database: {self.database}")
            self.connection = pyodbc.connect(connection_string)

            # Create SQLAlchemy engine for pandas compatibility
            encoded_password = quote_plus(self.password)
            encoded_username = quote_plus(self.username)
            sqlalchemy_url = f"mssql+pyodbc://{encoded_username}:{encoded_password}@{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
            self.engine = create_engine(sqlalchemy_url)

            print("Database connection successful!")
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