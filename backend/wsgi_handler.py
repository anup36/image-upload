"""WSGI Handler for AWS Lambda + API Gateway

This handler wraps the Flask application for Lambda execution.
"""

from app import app

def handler(event, context):
    """Lambda handler that wraps Flask app"""
    try:
        # For API Gateway proxy integration
        from werkzeug.wrappers import Request, Response
        import base64
        
        # Convert API Gateway event to WSGI environ
        environ = {
            'REQUEST_METHOD': event.get('httpMethod', 'GET'),
            'SCRIPT_NAME': '',
            'PATH_INFO': event.get('path', '/'),
            'QUERY_STRING': _encode_query_string(event.get('queryStringParameters', {})),
            'CONTENT_TYPE': event.get('headers', {}).get('content-type', ''),
            'CONTENT_LENGTH': str(len(event.get('body', ''))),
            'SERVER_NAME': 'lambda',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': _get_input_stream(event.get('body', ''), event.get('isBase64Encoded', False)),
            'wsgi.errors': None,
            'wsgi.multiprocess': False,
            'wsgi.multithread': False,
            'wsgi.run_once': False,
        }
        
        # Add headers
        for header, value in event.get('headers', {}).items():
            key = f"HTTP_{header.upper().replace('-', '_')}"
            environ[key] = value
        
        # Call Flask app
        response = Response.from_app(app, environ)
        
        # Convert Flask response to API Gateway format
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True),
            'isBase64Encoded': False
        }
    
    except Exception as e:
        print(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }

def _encode_query_string(params):
    """Encode query parameters"""
    if not params:
        return ''
    from urllib.parse import urlencode
    return urlencode(params)

def _get_input_stream(body, is_base64):
    """Get input stream from body"""
    from io import BytesIO
    import base64
    
    if not body:
        return BytesIO(b'')
    
    if is_base64:
        body = base64.b64decode(body)
    else:
        body = body.encode('utf-8')
    
    return BytesIO(body)