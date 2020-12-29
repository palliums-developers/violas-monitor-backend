import psycopg2
import json
from db.const import dsn

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if type(obj) not in (list, dict, str, int, float, bool):
        if hasattr(obj, "to_json"):
            return obj.to_json()
        return obj.__dict__

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
        try:
            conn = psycopg2.connect(self.dsn)
            cursor = conn.cursor()
            cursor.execute(cmd)
            result = cursor.fetchall()
            conn.close()
            return result
        except psycopg2.errors.UndefinedColumn as e:
            return None

    def keep(self, key, json_value):
        values = f"('{self.get_key(key)}', '{json.dumps(json_value, default=set_default)}')"
        sql = f'''
        INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
        SET value=excluded.value
        '''
        self.execute(sql)

    def get(self, key, value=None):
        sql = f"SELECT * FROM monitor WHERE KEY = '{self.get_key(key)}' "
        result = self.query(sql)
        if len(result):
            return result[0][1]
        return value

    def get_key(self, key):
        return self.PREFIX + key
