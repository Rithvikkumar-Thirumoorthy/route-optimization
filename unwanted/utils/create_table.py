#!/usr/bin/env python3
"""
Create routeplan_ai table if it doesn't exist
"""

from database import DatabaseConnection

def create_routeplan_table():
    """Create the routeplan_ai table"""
    db = DatabaseConnection()
    connection = db.connect()

    if not connection:
        print("Failed to connect to database")
        return False

    try:
        # Check if table exists
        check_table_query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = 'routeplan_ai'
        """

        result = db.execute_query(check_table_query)
        table_exists = result[0][0] > 0 if result else False

        if table_exists:
            print("routeplan_ai table already exists")
        else:
            # Create the table
            create_table_query = """
            CREATE TABLE routeplan_ai (
                id INT IDENTITY(1,1) PRIMARY KEY,
                salesagent NVARCHAR(100),
                custno NVARCHAR(50),
                custype NVARCHAR(20),
                latitude FLOAT,
                longitude FLOAT,
                stopno INT,
                routedate DATE,
                barangay NVARCHAR(100),
                barangay_code NVARCHAR(50),
                is_visited BIT DEFAULT 0,
                created_date DATETIME DEFAULT GETDATE()
            )
            """

            cursor = connection.cursor()
            cursor.execute(create_table_query)
            connection.commit()
            print("routeplan_ai table created successfully!")

        return True

    except Exception as e:
        print(f"Error creating table: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_routeplan_table()