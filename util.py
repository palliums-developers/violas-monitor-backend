def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if type(obj) not in (list, dict, str, int, float, bool):
        return obj.__dict__