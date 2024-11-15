import json
from collections import defaultdict
from django.core.exceptions import ValidationError


def serialize_errors(errors):
    def serialize_error(error):
        if isinstance(error, ValidationError):
            return error.messages
        if isinstance(error, list):
            return [serialize_error(e) for e in error]
        if isinstance(error, dict):
            return {k: serialize_error(v) for k, v in error.items()}
        if isinstance(error, defaultdict):
            return {k: serialize_error(v) for k, v in error.items()}
        return str(error)

    return json.dumps({int(k): serialize_error(v) for k, v in errors.items()})
