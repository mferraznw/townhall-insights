"""
AI enrichment pipeline using Azure OpenAI and Azure AI Language services
"""
import logging
import json
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
# Text Analytics imports removed - using Azure OpenAI instead
from .config import config


class AIEnrichment:
    """AI enrichment pipeline for transcript analysis"""
    
    def __init__(self):
        try:
            logging.info("Initializing AIEnrichment...")
            logging.info(f"Azure OpenAI endpoint: {config.azure_openai_endpoint}")
            logging.info(f"Azure OpenAI deployment: {config.azure_openai_deployment_name}")
            logging.info(f"API key present: {'Yes' if config.azure_openai_api_key else 'No'}")
            
            # Initialize Azure OpenAI client (v1.x syntax)
            self.openai_client = AzureOpenAI(
                api_key=config.azure_openai_api_key,
                api_version="2025-01-01-preview",
                azure_endpoint=config.azure_openai_endpoint
            )
            
            logging.info("Azure OpenAI client initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Text Analytics client is no longer needed since we use Azure OpenAI
        self.text_analytics_client = None
        logging.info("Using Azure OpenAI for sentiment analysis and entity extraction")
    
    def analyze_sentiment(self, text: str) -> float:
        # Use Azure OpenAI for sentiment analysis instead of Text Analytics
        try:
            response = self.openai_client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis expert. Analyze the sentiment of the given text and return only a number between -1 (very negative) and 1 (very positive). Return 0 for neutral."},
                    {"role": "user", "content": f"Analyze sentiment of: {text}"}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            # Parse the response to get a sentiment score
            sentiment_text = response.choices[0].message.content.strip()
            try:
                sentiment_score = float(sentiment_text)
                return max(-1.0, min(1.0, sentiment_score))  # Clamp between -1 and 1
            except ValueError:
                # If we can't parse as float, try to interpret the text
                sentiment_text_lower = sentiment_text.lower()
                if "positive" in sentiment_text_lower:
                    return 0.5
                elif "negative" in sentiment_text_lower:
                    return -0.5
                else:
                    return 0.0
                
        except Exception as e:
            logging.error(f"Sentiment analysis error: {str(e)}")
            return 0.0
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        # Use Azure OpenAI for entity extraction instead of Text Analytics
        try:
            response = self.openai_client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an entity extraction expert. Extract entities from the given text and return a JSON object with arrays for 'persons', 'organizations', 'locations', and 'other'. Return empty arrays if no entities found."},
                    {"role": "user", "content": f"Extract entities from: {text}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse the response to get entities
            entities_text = response.choices[0].message.content.strip()
            try:
                import json
                entities = json.loads(entities_text)
                return {
                    "persons": entities.get("persons", []),
                    "organizations": entities.get("organizations", []),
                    "locations": entities.get("locations", []),
                    "other": entities.get("other", [])
                }
            except (json.JSONDecodeError, KeyError):
                # If we can't parse as JSON, return empty entities
                return {"persons": [], "organizations": [], "locations": [], "other": []}
                
        except Exception as e:
            logging.error(f"Entity extraction error: {str(e)}")
            return {"persons": [], "organizations": [], "locations": [], "other": []}
    
    def generate_topics(self, utterances: List[str]) -> List[str]:
        try:
            embeddings = []
            for utterance in utterances:
                response = self.openai_client.embeddings.create(
                    input=utterance,
                    model=config.azure_openai_embedding_deployment
                )
                embeddings.append(response.data[0].embedding)
            
            topics = []
            combined_text = " ".join(utterances).lower()
            
            topic_keywords = {
                "sugar_reduction": ["sugar", "sweetener", "low sugar", "zero sugar"],
                "packaging": ["packaging", "bottle", "can", "container", "rPET"],
                "sustainability": ["sustainable", "environment", "carbon", "recycling"],
                "market_trends": ["market", "trend", "consumer", "demand"],
                "operations": ["production", "manufacturing", "supply", "logistics"],
                "innovation": ["innovation", "new product", "development", "research"]
            }
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    topics.append(topic)
            
            return topics if topics else ["general_discussion"]
            
        except Exception as e:
            logging.error(f"Topic generation error: {str(e)}")
            return ["general_discussion"]
    
    def summarize_meeting(self, utterances: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            logging.info(f"Starting meeting summarization for {len(utterances)} utterances")
            
            meeting_text = "\n".join([
                f"{utterance.get('speaker', 'Unknown')}: {utterance.get('content', '')}"
                for utterance in utterances
            ])
            
            logging.info(f"Meeting text length: {len(meeting_text)} characters")
            
            prompt = f"""
            Analyze this townhall meeting transcript and provide a JSON response with:
            1. A concise summary of key discussion points
            2. List of action items mentioned
            3. List of risks or concerns raised
            4. Overall sentiment assessment
            
            Transcript:
            {meeting_text}
            
            Respond with valid JSON in this format:
            {{
                "summary": "Brief summary of the meeting",
                "actions": ["action item 1", "action item 2"],
                "risks": ["risk 1", "risk 2"],
                "sentiment_overall": "positive/negative/neutral"
            }}
            """
            
            logging.info(f"Calling Azure OpenAI with deployment: {config.azure_openai_deployment_name}")
            logging.info(f"Using endpoint: {config.azure_openai_endpoint}")
            
            response = self.openai_client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            logging.info(f"Azure OpenAI response received")
            summary_text = response.choices[0].message.content
            logging.info(f"Summary text length: {len(summary_text)} characters")
            
            result = json.loads(summary_text)
            logging.info(f"Successfully parsed summary JSON")
            return result
            
        except Exception as e:
            logging.error(f"Meeting summarization error: {str(e)}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {
                "summary": "Unable to generate summary",
                "actions": [],
                "risks": [],
                "sentiment_overall": "neutral"
            }
    
    def enrich_utterances(self, utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        
        for utterance in utterances:
            sentiment_score = self.analyze_sentiment(utterance["content"])
            entities = self.extract_entities(utterance["content"])
            
            enriched_utterance = utterance.copy()
            enriched_utterance["sentiment_score"] = sentiment_score
            enriched_utterance["entities"] = entities
            
            if entities["organizations"]:
                org = entities["organizations"][0].lower()
                if "marketing" in org:
                    enriched_utterance["department"] = "Marketing"
                elif "operations" in org:
                    enriched_utterance["department"] = "Operations"
                elif "finance" in org:
                    enriched_utterance["department"] = "Finance"
                else:
                    enriched_utterance["department"] = "General"
            
            if entities["locations"]:
                location = entities["locations"][0].lower()
                if "north america" in location or "us" in location:
                    enriched_utterance["region"] = "North America"
                elif "europe" in location or "emea" in location:
                    enriched_utterance["region"] = "EMEA"
                elif "asia" in location:
                    enriched_utterance["region"] = "Asia Pacific"
                else:
                    enriched_utterance["region"] = "Global"
            
            enriched.append(enriched_utterance)
        
        return enriched
