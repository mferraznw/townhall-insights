"""
Minimal test upload function
"""
import json
import azure.functions as func
from shared.transcript_parser import TranscriptParser

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test upload function
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
        
        # Read file content
        file_content = file.read()
        
        # Parse transcript
        parser = TranscriptParser()
        transcript_text = file_content.decode('utf-8')
        utterances = parser.parse_vtt(transcript_text)
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "filename": filename,
                "utterances_count": len(utterances),
                "first_utterance": utterances[0] if utterances else None
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

