"""
Simple upload test without any shared modules
"""
import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple upload test
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
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "filename": filename,
                "file_size": len(file_content),
                "content_preview": file_content.decode('utf-8')[:100]
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

