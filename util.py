def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if type(obj) not in (list, dict, str, int, float, bool):
        if hasattr(obj, "to_json"):
            return obj.to_json()
        return obj.__dict__