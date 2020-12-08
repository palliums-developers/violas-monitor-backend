import json
from db.base import Base

class GeneralApi(Base):
    def __init__(self):
        super().__init__()

    def set_key(self, key, value):
        values = f"('{key}', '{json.dumps(value)}')"
        sql = f'''
        INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
        SET value=excluded.value;
        '''
        self.execute(sql)

    def get_key(self, key):
        sql = f"SELECT * FROM monitor WHERE key='{key}'"
        value = self.query(sql)
        if len(value):
            return self.query(sql)[0][1]

general_api = GeneralApi()

if __name__ == "__main__":
    general_api.set_key("key", {"key": "value"})
    print(general_api.get_key("key"))

