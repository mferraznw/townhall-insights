"""
Insights speakers endpoint - Get speaker analysis and sentiment
"""
import logging
import json
from collections import defaultdict
import azure.functions as func
from shared.data_storage import DataStorage


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get speaker analysis and sentiment data
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
        
        # Get utterances from data storage
        storage = DataStorage()
        utterances = storage.search_utterances(filters=filters, top=1000)
        
        # Analyze speakers
        speaker_data = defaultdict(lambda: {
            'speaker_id': '',
            'display_name': '',
            'department': '',
            'region': '',
            'country': '',
            'mentions': 0,
            'sentiment_scores': [],
            'quotes': []
        })
        
        for utterance in utterances:
            speaker = utterance.get('speaker', 'Unknown')
            
            if speaker not in speaker_data:
                speaker_data[speaker] = {
                    'speaker_id': f"spk-{speaker.lower().replace(' ', '')}",
                    'display_name': speaker,
                    'department': utterance.get('department', 'Unknown'),
                    'region': utterance.get('region', 'Unknown'),
                    'country': 'US',  # Default, would be extracted from entities
                    'mentions': 0,
                    'sentiment_scores': [],
                    'quotes': []
                }
            
            speaker_data[speaker]['mentions'] += 1
            sentiment_score = utterance.get('sentiment_score', 0.0)
            speaker_data[speaker]['sentiment_scores'].append(sentiment_score)
            
            # Add exemplar quotes (limit to 3 per speaker)
            if len(speaker_data[speaker]['quotes']) < 3:
                speaker_data[speaker]['quotes'].append({
                    'quote': utterance.get('content', '')[:200] + '...' if len(utterance.get('content', '')) > 200 else utterance.get('content', ''),
                    'meeting_id': utterance.get('meeting_id', ''),
                    'ts': utterance.get('start_timestamp', '00:00')
                })
        
        # Calculate average sentiment and format results
        results = []
        for speaker, data in speaker_data.items():
            avg_sentiment = sum(data['sentiment_scores']) / len(data['sentiment_scores']) if data['sentiment_scores'] else 0.0
            
            result = {
                'speaker_id': data['speaker_id'],
                'display_name': data['display_name'],
                'department': data['department'],
                'region': data['region'],
                'country': data['country'],
                'mentions': data['mentions'],
                'avg_sentiment': round(avg_sentiment, 2),
                'exemplar_quotes': data['quotes']
            }
            results.append(result)
        
        # Sort by mentions (most active speakers first)
        results.sort(key=lambda x: x['mentions'], reverse=True)
        
        response_data = {
            'results': results
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Speakers endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
