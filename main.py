from dataclasses import dataclass
from dataclasses import dataclass
import json

@dataclass
class Test():
    value : list = ()

test= Test([])
print(json.dumps(test.__dict__))


