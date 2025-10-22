"""
Simple upload function without shared modules
"""
import json
import uuid
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple upload function
    """
    try:
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
        
        # Generate meeting ID
        meeting_id = f"meeting-{uuid.uuid4().hex[:8]}"
        
        # Mock utterances for testing
        utterances = [
            {
                "utterance_id": str(uuid.uuid4()),
                "speaker": "James Robinson",
                "content": "Welcome everyone, today we're focusing on AI improvements.",
                "start_time": "00:00:01.000",
                "end_time": "00:00:06.000",
                "duration": 5.0,
                "meeting_id": meeting_id
            },
            {
                "utterance_id": str(uuid.uuid4()),
                "speaker": "Sarah Chen",
                "content": "Thank you James. We've seen 23% improvements in forecasting accuracy.",
                "start_time": "00:00:07.000",
                "end_time": "00:00:12.000",
                "duration": 5.0,
                "meeting_id": meeting_id
            }
        ]
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "meeting_id": meeting_id,
                "filename": filename,
                "utterances_count": len(utterances),
                "message": "Transcript processed successfully (mock data)"
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

