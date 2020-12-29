import json
from db.base import Base

class GeneralApi(Base):
    PREFIX = ""

general_api = GeneralApi()

if __name__ == "__main__":
    general_api.keep("key", {111: "value"})
    print(general_api.get("key"))

