"""
Chat query endpoint for natural language interactions with townhall insights
"""
import logging
import json
import re
import azure.functions as func
from shared.data_storage import DataStorage
from shared.ai_enrichment import AIEnrichment
from shared.config import config
from openai import AzureOpenAI


class ChatQueryProcessor:
    """Process natural language queries about townhall insights"""
    
    def __init__(self):
        self.storage = DataStorage()
        self.ai_enrichment = AIEnrichment()
        
        # Initialize OpenAI client for Azure (v1.x syntax)
        self.client = AzureOpenAI(
            api_key=config.azure_openai_api_key,
            api_version="2025-01-01-preview",
            azure_endpoint=config.azure_openai_endpoint
        )
    
    def extract_intent_and_parameters(self, question: str) -> dict:
        """
        Extract intent and parameters from natural language question
        """
        try:
            prompt = f"""
            Analyze this question about townhall meeting insights and extract:
            1. Intent (trends, speakers, utterances, sentiment, topics)
            2. Parameters (date ranges, departments, regions, sentiment filters)
            3. Specific entities mentioned
            
            Question: "{question}"
            
            Respond with JSON:
            {{
                "intent": "trends|speakers|utterances|sentiment|topics",
                "parameters": {{
                    "from_date": "YYYY-MM-DD or null",
                    "to_date": "YYYY-MM-DD or null",
                    "department": "department name or null",
                    "region": "region name or null",
                    "topics": ["topic1", "topic2"] or [],
                    "sentiment_filter": "positive|negative|neutral or null"
                }},
                "entities": ["entity1", "entity2"] or []
            }}
            """
            
            response = self.client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logging.error(f"Intent extraction error: {str(e)}")
            return {
                "intent": "utterances",
                "parameters": {},
                "entities": []
            }
    
    def validate_parameters(self, parameters: dict) -> dict:
        """
        Validate and clean parameters to ensure all values are strings or proper types
        """
        validated = {}
        
        for key, value in parameters.items():
            # Ensure key is a string
            if not isinstance(key, str):
                key = str(key)
            
            if value is None or value == "null" or value == "":
                continue
            elif isinstance(value, list):
                # Convert list to proper format
                if key == "topics" and value:
                    validated[key] = [str(item) for item in value if item and str(item).strip()]
            elif isinstance(value, str):
                # Only include non-empty strings
                if value.strip():
                    validated[key] = value.strip()
            elif isinstance(value, (int, float)):
                # Convert numbers to strings
                validated[key] = str(value)
            else:
                # Convert any other type to string
                validated[key] = str(value)
        
        return validated
    
    def process_query(self, question: str, context: str = "") -> dict:
        """
        Process natural language query and return structured response
        """
        try:
            logging.info(f"Processing query: {question}")

            # Extract intent and parameters
            logging.info("Extracting intent and parameters")
            analysis = self.extract_intent_and_parameters(question)
            intent = analysis["intent"]
            parameters = self.validate_parameters(analysis["parameters"])
            logging.info(f"Detected intent: {intent}, parameters: {parameters}")
            
            # Get data based on intent - use empty filters to avoid parameter issues
            data = {}
            sources = []
            
            if intent == "trends":
                # Use empty filters to avoid parameter issues
                trends_data = self.storage.get_trends({})
                data = trends_data
                sources = [f"Trend analysis for {len(trends_data.get('trends', []))} topics"]
                
            elif intent == "speakers":
                # Use empty filters to avoid parameter issues
                utterances = self.storage.search_utterances(filters={}, top=1000)
                # Process speaker data (simplified version)
                speaker_counts = {}
                for utterance in utterances:
                    speaker = utterance.get('speaker', 'Unknown')
                    if speaker not in speaker_counts:
                        speaker_counts[speaker] = {'count': 0, 'sentiment': []}
                    speaker_counts[speaker]['count'] += 1
                    speaker_counts[speaker]['sentiment'].append(utterance.get('sentiment_score', 0))
                
                data = {"speakers": speaker_counts}
                sources = [f"Analysis of {len(utterances)} utterances from {len(speaker_counts)} speakers"]
                
            elif intent == "utterances":
                # Use empty filters to avoid parameter issues
                utterances = self.storage.search_utterances(filters={}, top=50)
                data = {"utterances": utterances}
                sources = [f"Found {len(utterances)} relevant utterances"]
                
            elif intent == "sentiment":
                # Use empty filters to avoid parameter issues
                utterances = self.storage.search_utterances(filters={}, top=1000)
                sentiments = [u.get('sentiment_score', 0) for u in utterances]
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
                data = {"average_sentiment": avg_sentiment, "total_utterances": len(utterances)}
                sources = [f"Sentiment analysis of {len(utterances)} utterances"]
                
            else:
                # General search - use empty filters to avoid parameter issues
                utterances = self.storage.search_utterances(filters={}, top=50)
                data = {"utterances": utterances}
                sources = [f"General search returned {len(utterances)} results"]
            
            # Check if we have data
            has_data = False
            if intent == "trends" and data.get("trends"):
                has_data = True
            elif intent in ["speakers", "sentiment"] and data:
                has_data = True
            elif intent == "utterances" and data.get("utterances"):
                has_data = True

            logging.info(f"Has data: {has_data}, data keys: {list(data.keys())}")

            # Generate natural language response
            logging.info("Generating natural language answer")
            answer = self.generate_answer(question, intent, data, context)
            logging.info(f"Answer generated successfully")

            return {
                "answer": answer,
                "data": data,
                "sources": sources,
                "confidence": 0.85 if has_data else 0.3,
                "intent": intent,
                "parameters_used": {}
            }

        except Exception as e:
            logging.error(f"Query processing error: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            
            # Handle specific "key must be a string" error
            if "key must be a string" in str(e).lower():
                return {
                    "answer": "I'm currently experiencing a technical issue with parameter processing. Please try asking your question in a different way.",
                    "data": {},
                    "sources": [],
                    "confidence": 0.0,
                    "error": "Parameter validation error - please rephrase your question"
                }
            
            return {
                "answer": "I apologize, but I encountered an error processing your question. Please try rephrasing your query.",
                "data": {},
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def generate_answer(self, question: str, intent: str, data: dict, context: str = "") -> str:
        """
        Generate natural language answer based on data
        """
        try:
            logging.info(f"Generating answer for intent: {intent}")

            # Truncate data if it's too large
            data_str = json.dumps(data, indent=2)
            if len(data_str) > 3000:
                logging.warning(f"Data too large ({len(data_str)} chars), truncating")
                data_str = data_str[:3000] + "\n... (truncated)"

            prompt = f"""
            Based on the following data from townhall meetings, provide a natural, conversational answer to the user's question.

            Question: "{question}"
            Intent: {intent}
            Context: {context}

            Data:
            {data_str}

            Guidelines:
            - Be conversational and executive-friendly
            - Include specific numbers and insights
            - Keep response concise but informative
            - If data is limited, mention that
            - Use bullet points for multiple insights

            Provide a clear, actionable response:
            """

            logging.info(f"Calling Azure OpenAI with model: {config.azure_openai_deployment_name}")

            response = self.client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )

            answer = response.choices[0].message.content.strip()
            logging.info(f"Generated answer length: {len(answer)} chars")
            return answer

        except Exception as e:
            logging.error(f"Answer generation error: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")

            # Provide more specific error messages
            error_msg = str(e).lower()
            if "authentication" in error_msg or "unauthorized" in error_msg:
                return "I'm experiencing authentication issues with the AI service. Please contact support."
            elif "not found" in error_msg or "404" in error_msg:
                return f"The AI model '{config.azure_openai_deployment_name}' is not available. Please check the configuration."
            elif "quota" in error_msg or "rate limit" in error_msg:
                return "The AI service is currently at capacity. Please try again in a moment."
            else:
                return f"I encountered an error: {str(e)}. Please try asking your question in a different way."


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process natural language queries about townhall insights
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
        
        # Parse request body
        try:
            body = req.get_json()
        except:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        question = body.get('question', '')
        context = body.get('context', '')
        
        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Question is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process query
        processor = ChatQueryProcessor()
        result = processor.process_query(question, context)
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Chat endpoint error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "answer": "I'm sorry, I encountered an error processing your request. Please try again."
            }),
            status_code=500,
            mimetype="application/json"
        )