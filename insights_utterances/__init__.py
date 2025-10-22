"""
Insights utterances endpoint - Get searchable utterances with filtering
"""
import logging
import json
import azure.functions as func
from shared.data_storage import DataStorage


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get searchable utterances with filtering and pagination
    """
    try:
        # Parse query parameters
        params = req.params
        
        # Search text
        search_text = params.get('search', '')
        
        # Filters
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
        
        # Pagination
        try:
            top = int(params.get('top', 50))
            skip = int(params.get('skip', 0))
        except ValueError:
            top = 50
            skip = 0
        
        # Limit top to prevent excessive results
        top = min(top, 100)
        
        # Get utterances from data storage
        storage = DataStorage()
        utterances = storage.search_utterances(
            search_text=search_text if search_text else None,
            filters=filters,
            top=top,
            skip=skip
        )
        
        # Format utterances for response
        items = []
        for utterance in utterances:
            item = {
                'utterance_id': utterance.get('id', ''),
                'meeting_id': utterance.get('meeting_id', ''),
                'speaker': utterance.get('speaker', ''),
                'department': utterance.get('department', ''),
                'region': utterance.get('region', ''),
                'country': 'US',  # Default, would be extracted from entities
                'start_ts': utterance.get('start_timestamp', ''),
                'end_ts': utterance.get('end_timestamp', ''),
                'sentiment_score': utterance.get('sentiment_score', 0.0),
                'content': utterance.get('content', ''),
                'topics': utterance.get('topics', []),
                'link_to_clip': f"https://teams.microsoft.com/meeting/{utterance.get('meeting_id', '')}"  # Placeholder
            }
            items.append(item)
        
        response_data = {
            'items': items,
            'total_count': len(items),
            'search_text': search_text,
            'filters_applied': filters,
            'pagination': {
                'top': top,
                'skip': skip,
                'has_more': len(items) == top  # Simple check for more results
            }
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Utterances endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
