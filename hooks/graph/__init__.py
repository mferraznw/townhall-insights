"""
Microsoft Graph webhook endpoint for Teams transcript ingestion
"""
import logging
import json
import uuid
import requests
import azure.functions as func
from msal import ConfidentialClientApplication
from shared.transcript_parser import TranscriptParser
from shared.ai_enrichment import AIEnrichment
from shared.data_storage import DataStorage
from shared.config import config


def get_graph_access_token() -> str:
    """
    Get access token for Microsoft Graph API
    """
    try:
        app = ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}"
        )
        
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
            
    except Exception as e:
        logging.error(f"Graph token acquisition error: {str(e)}")
        raise


def get_teams_transcript(access_token: str, meeting_id: str) -> dict:
    """
    Get Teams meeting transcript from Graph API
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get meeting recordings
        recordings_url = f"{config.graph_api_endpoint}/communications/onlineMeetings/{meeting_id}/recordings"
        recordings_response = requests.get(recordings_url, headers=headers)
        
        if recordings_response.status_code != 200:
            raise Exception(f"Failed to get recordings: {recordings_response.status_code}")
        
        recordings = recordings_response.json()
        
        # Get transcript from the first recording (simplified approach)
        if not recordings.get('value'):
            raise Exception("No recordings found for meeting")
        
        recording = recordings['value'][0]
        transcript_url = recording.get('transcript')
        
        if not transcript_url:
            raise Exception("No transcript available for recording")
        
        # Download transcript content
        transcript_response = requests.get(transcript_url, headers=headers)
        if transcript_response.status_code != 200:
            raise Exception(f"Failed to download transcript: {transcript_response.status_code}")
        
        return {
            'content': transcript_response.text,
            'format': 'vtt',
            'meeting_id': meeting_id,
            'recording_id': recording.get('id')
        }
        
    except Exception as e:
        logging.error(f"Graph API error: {str(e)}")
        raise


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle Microsoft Graph webhook for Teams transcript ingestion
    """
    try:
        # Handle webhook validation (GET request)
        if req.method == 'GET':
            validation_token = req.params.get('validationToken')
            if validation_token:
                return func.HttpResponse(validation_token, status_code=200)
            else:
                return func.HttpResponse("Validation token required", status_code=400)
        
        # Handle webhook notifications (POST request)
        if req.method == 'POST':
            try:
                body = req.get_json()
            except:
                return func.HttpResponse("Invalid JSON", status_code=400)
            
            # Process webhook notifications
            notifications = body.get('value', [])
            processed_meetings = []
            
            for notification in notifications:
                try:
                    # Extract meeting ID from notification
                    resource = notification.get('resource', '')
                    if '/communications/onlineMeetings/' not in resource:
                        continue
                    
                    meeting_id = resource.split('/communications/onlineMeetings/')[-1]
                    
                    # Get access token
                    access_token = get_graph_access_token()
                    
                    # Get transcript from Graph API
                    transcript_data = get_teams_transcript(access_token, meeting_id)
                    
                    # Parse transcript
                    parser = TranscriptParser()
                    utterances = parser.parse_vtt(transcript_data['content'])
                    
                    if not utterances:
                        continue
                    
                    # Normalize utterances
                    normalized_utterances = parser.normalize_utterances(utterances, meeting_id)
                    
                    # AI enrichment
                    ai_enrichment = AIEnrichment()
                    enriched_utterances = ai_enrichment.enrich_utterances(normalized_utterances)
                    
                    # Generate topics
                    utterance_texts = [u["content"] for u in enriched_utterances]
                    topics = ai_enrichment.generate_topics(utterance_texts)
                    
                    # Add topics to utterances
                    for utterance in enriched_utterances:
                        utterance["topics"] = topics
                    
                    # Store data
                    storage = DataStorage()
                    storage.store_transcript(meeting_id, transcript_data['content'], 'vtt')
                    storage.store_utterances(enriched_utterances)
                    
                    processed_meetings.append({
                        'meeting_id': meeting_id,
                        'utterances_count': len(enriched_utterances),
                        'status': 'success'
                    })
                    
                except Exception as e:
                    logging.error(f"Error processing meeting notification: {str(e)}")
                    processed_meetings.append({
                        'meeting_id': meeting_id if 'meeting_id' in locals() else 'unknown',
                        'status': 'error',
                        'error': str(e)
                    })
            
            return func.HttpResponse(
                json.dumps({
                    'processed_meetings': processed_meetings,
                    'total_notifications': len(notifications)
                }),
                status_code=200,
                mimetype="application/json"
            )
        
        return func.HttpResponse("Method not allowed", status_code=405)
        
    except Exception as e:
        logging.error(f"Graph webhook error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
