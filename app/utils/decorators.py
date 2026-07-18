from functools import wraps
from flask import make_response

def nocache(view):
    """Decorator to disable caching for a view"""
    @wraps(view)
    def no_cache(*args, **kwargs):
        resp = make_response(view(*args, **kwargs))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return no_cache

def add_header(response):
    """After request handler to add cache control headers"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
