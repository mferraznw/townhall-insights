"""
Simple test function to verify the Function App is working
"""
import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple test endpoint
    """
    try:
        return func.HttpResponse(
            json.dumps({"message": "Function App is working!", "status": "success"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
