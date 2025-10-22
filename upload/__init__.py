"""
File upload endpoint for transcript files (.vtt and .docx)
"""
import logging
import sys
import uuid
import json
import azure.functions as func
from shared.transcript_parser import TranscriptParser
from shared.ai_enrichment import AIEnrichment
from shared.data_storage import DataStorage

from datetime import datetime, timezone

# Force logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)

def ensure_datetime_format(dt_value):
    """Ensure datetime is in proper ISO format with timezone"""
    if isinstance(dt_value, str):
        # If it's already a string, try to parse and reformat
        try:
            dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            return dt.isoformat() + 'Z' if not dt.tzinfo else dt.isoformat()
        except:
            return dt_value
    elif isinstance(dt_value, datetime):
        # If it's a datetime object, ensure it has timezone
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        return dt_value.isoformat()
    return dt_value
    
def main(req: func.HttpRequest) -> func.HttpResponse:

    print("=" * 50)
    print("UPLOAD FUNCTION CALLED")
    print("=" * 50)
    try:
        # Authentication temporarily disabled for testing
        
        # Get uploaded file
        files = req.files
        if not files:
            return func.HttpResponse(
                json.dumps({"error": "No file uploaded"}),
                status_code=400,
                mimetype="application/json"
            )
        
        file = list(files.values())[0]
        filename = file.filename
        
        if not filename:
            return func.HttpResponse(
                json.dumps({"error": "No filename provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate file type
        file_extension = filename.lower().split('.')[-1]
        if file_extension not in ['vtt', 'docx']:
            return func.HttpResponse(
                json.dumps({"error": "Unsupported file type. Only .vtt and .docx files are allowed"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Generate meeting ID
        meeting_id = f"meeting-{uuid.uuid4().hex[:8]}"
        
        # Read file content
        file_content = file.read()
        
        # Parse transcript based on file type
        parser = TranscriptParser()
        
        if file_extension == 'vtt':
            transcript_text = file_content.decode('utf-8')
            utterances = parser.parse_vtt(transcript_text)
        else:  # docx
            utterances = parser.parse_docx(file_content)
        
        if not utterances:
            return func.HttpResponse(
                json.dumps({"error": "No utterances found in transcript"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get meeting date from form data
        meeting_date = req.form.get('meeting_date', '2025-01-01')
        
        # Normalize utterances for storage
        normalized_utterances = parser.normalize_utterances(utterances, meeting_id, meeting_date)
        
        # AI enrichment (with fallback if it fails)
        try:
            logging.info("Initializing AI enrichment")
            ai_enrichment = AIEnrichment()

            # Enrich utterances with AI analysis
            logging.info(f"Enriching {len(normalized_utterances)} utterances")
            enriched_utterances = ai_enrichment.enrich_utterances(normalized_utterances)

            # Generate topics for the meeting
            utterance_texts = [u["content"] for u in enriched_utterances]
            logging.info(f"Generating topics from {len(utterance_texts)} utterances")
            topics = ai_enrichment.generate_topics(utterance_texts)
            logging.info(f"Generated topics: {topics}")

            # Add topics to all utterances
            for utterance in enriched_utterances:
                utterance["topics"] = topics

            # Generate meeting summary
            logging.info("Generating meeting summary")
            meeting_summary = ai_enrichment.summarize_meeting(enriched_utterances)
            logging.info("AI enrichment completed successfully")

        except Exception as e:
            logging.warning(f"AI enrichment failed, using basic data: {str(e)}")
            import traceback
            logging.warning(f"AI enrichment traceback: {traceback.format_exc()}")
            # Use normalized utterances without AI enrichment
            enriched_utterances = normalized_utterances
            topics = ["general_discussion"]
            meeting_summary = {"summary": "Unable to generate summary", "actions": [], "risks": [], "sentiment_overall": "neutral"}
        
        # Store data
        storage = DataStorage()
        
        # Ensure search index exists
        try:
            logging.info("Ensuring search index exists")
            index_created = storage.create_search_index()
            logging.info(f"Search index creation result: {index_created}")
        except Exception as e:
            logging.error(f"Failed to create search index: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            # Continue anyway - index might already exist
        
        # Store raw transcript
        transcript_content = transcript_text if file_extension == 'vtt' else file_content.decode('utf-8')
        storage.store_transcript(meeting_id, transcript_content, file_extension)
        
        # Store enriched utterances in search index
        print(f"*** ABOUT TO STORE {len(enriched_utterances)} UTTERANCES ***")
        try:
            logging.info(f"Attempting to store {len(enriched_utterances)} utterances")
            
            # Fix datetime formats before storing
            for utterance in enriched_utterances:
                if 'created_at' in utterance:
                    utterance['created_at'] = ensure_datetime_format(utterance['created_at'])
                if 'updated_at' in utterance:
                    utterance['updated_at'] = ensure_datetime_format(utterance['updated_at'])
                if 'meeting_date' in utterance:
                    utterance['meeting_date'] = ensure_datetime_format(utterance['meeting_date'])
                # Remove entities field - not in search index schema
                if 'entities' in utterance:
                    del utterance['entities']
            
            result = storage.store_utterances(enriched_utterances)
            logging.info(f"Store utterances result: {result}")
        except Exception as e:
            logging.error(f"Failed to store utterances: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Return success response
        response_data = {
            "meeting_id": meeting_id,
            "filename": filename,
            "utterances_count": len(enriched_utterances),
            "topics": topics,
            "summary": meeting_summary,
            "status": "success"
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )