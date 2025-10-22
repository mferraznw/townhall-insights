"""
Insights trends endpoint - Get trending topics and sentiment analysis
"""
import logging
import json
import azure.functions as func
from shared.data_storage import DataStorage


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get trending topics and sentiment analysis
    """
    try:
        # Check if request is from localhost (for development)
        client_ip = req.headers.get('X-Forwarded-For', req.headers.get('X-Real-IP', ''))
        host = req.headers.get('Host', '')
        is_localhost = (
            'localhost' in host or 
            '127.0.0.1' in host or 
            client_ip in ['127.0.0.1', '::1'] or
            req.headers.get('X-Forwarded-Host', '').startswith('localhost')
        )
        
        # For localhost requests, skip authentication check
        if not is_localhost:
            # Check for function key in query parameters or headers
            function_key = req.params.get('code') or req.headers.get('x-functions-key')
            if not function_key:
                return func.HttpResponse(
                    json.dumps({"error": "Function key required for non-localhost requests"}),
                    status_code=401,
                    mimetype="application/json"
                )
        
        # Parse query parameters
        params = req.params
        
        filters = {}
        
        if 'from' in params:
            filters['from_date'] = params['from']
        if 'to' in params:
            filters['to_date'] = params['to']
        if 'topicsCsv' in params:
            filters['topics'] = params['topicsCsv'].split(',')
        if 'region' in params:
            filters['region'] = params['region']
        if 'department' in params:
            filters['department'] = params['department']
        if 'sentiment_min' in params:
            try:
                filters['sentiment_min'] = float(params['sentiment_min'])
            except ValueError:
                pass
        if 'sentiment_max' in params:
            try:
                filters['sentiment_max'] = float(params['sentiment_max'])
            except ValueError:
                pass
        
        # Get trends from data storage
        storage = DataStorage()
        trends_data = storage.get_trends(filters)
        
        return func.HttpResponse(
            json.dumps(trends_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Trends endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
