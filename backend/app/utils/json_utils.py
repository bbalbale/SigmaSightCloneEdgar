import json
from datetime import date, datetime
from decimal import Decimal

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def to_json(data):
    return json.dumps(data, cls=CustomJSONEncoder, indent=4)
