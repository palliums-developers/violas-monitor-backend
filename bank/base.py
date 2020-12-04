import psycopg2
from .const import dsn

class Base():
    def __init__(self):
        self.dsn = dsn

    def execute(self, cmd, data=None):
        conn = psycopg2.connect(self.dsn)
        cursor = conn.cursor()
        if data is None:
            cursor.execute(cmd)
        else:
            cursor.execute(cmd, (data,))
        conn.commit()
        conn.close()

    def query(self, cmd):
        conn = psycopg2.connect(self.dsn)
        cursor = conn.cursor()
        cursor.execute(cmd)
        result = cursor.fetchall()
        conn.close()
        return result
