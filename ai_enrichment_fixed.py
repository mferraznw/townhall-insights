"""
AI enrichment pipeline using Azure OpenAI and Azure AI Language services
"""
import logging
import json
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from azure.cognitiveservices.language.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from .config import config


class AIEnrichment:
    """AI enrichment pipeline for transcript analysis"""
    
    def __init__(self):
        # Initialize Azure OpenAI client (v1.x syntax)
        self.openai_client = AzureOpenAI(
            api_key=config.azure_openai_api_key,
            api_version="2023-12-01-preview",
            azure_endpoint=config.azure_openai_endpoint
        )
        
        # Initialize Azure AI Language client (only if credentials available)
        if config.azure_ai_language_endpoint and config.azure_ai_language_key:
            try:
                self.text_analytics_client = TextAnalyticsClient(
                    endpoint=config.azure_ai_language_endpoint,
                    credentials=AzureKeyCredential(config.azure_ai_language_key)
                )
            except Exception as e:
                logging.warning(f"Could not initialize Text Analytics client: {e}")
                self.text_analytics_client = None
        else:
            self.text_analytics_client = None
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text using Azure AI Language
        Returns sentiment score between -1 (negative) and 1 (positive)
        """
        if not self.text_analytics_client:
            logging.warning("Text Analytics client not available, returning neutral sentiment")
            return 0.0
            
        try:
            response = self.text_analytics_client.analyze_sentiment([text])
            result = response[0]
            
            # Convert sentiment to numeric score
            if result.sentiment == "positive":
                return result.confidence_scores.positive
            elif result.sentiment == "negative":
                return -result.confidence_scores.negative
            else:  # neutral
                return 0.0
                
        except Exception as e:
            logging.error(f"Sentiment analysis error: {str(e)}")
            return 0.0
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities using Azure AI Language
        Returns dictionary with entity types and values
        """
        if not self.text_analytics_client:
            logging.warning("Text Analytics client not available, returning empty entities")
            return {"persons": [], "organizations": [], "locations": [], "other": []}
            
        try:
            response = self.text_analytics_client.recognize_entities([text])
            result = response[0]
            
            entities = {
                "persons": [],
                "organizations": [],
                "locations": [],
                "other": []
            }
            
            for entity in result.entities:
                if entity.category == "Person":
                    entities["persons"].append(entity.text)
                elif entity.category == "Organization":
                    entities["organizations"].append(entity.text)
                elif entity.category in ["Location", "Geography"]:
                    entities["locations"].append(entity.text)
                else:
                    entities["other"].append(entity.text)
            
            return entities
            
        except Exception as e:
            logging.error(f"Entity extraction error: {str(e)}")
            return {"persons": [], "organizations": [], "locations": [], "other": []}
    
    def generate_topics(self, utterances: List[str]) -> List[str]:
        """
        Generate topic clusters using OpenAI embeddings
        Returns list of topic names
        """
        try:
            # Get embeddings for all utterances
            embeddings = []
            for utterance in utterances:
                response = self.openai_client.embeddings.create(
                    input=utterance,
                    model=config.azure_openai_embedding_deployment
                )
                embeddings.append(response.data[0].embedding)
            
            # Simple clustering approach - in production, use proper clustering algorithm
            # For now, return generic topics based on content analysis
            topics = []
            combined_text = " ".join(utterances).lower()
            
            # Topic detection based on keywords
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
        """
        Generate meeting summary using Azure OpenAI
        Returns summary with actions, risks, and overall sentiment
        """
        try:
            # Combine all utterances into meeting text
            meeting_text = "\n".join([
                f"{utterance['speaker']}: {utterance['content']}" 
                for utterance in utterances
            ])
            
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
            
            response = self.openai_client.chat.completions.create(
                model=config.azure_openai_deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            summary_text = response.choices[0].message.content
            return json.loads(summary_text)
            
        except Exception as e:
            logging.error(f"Meeting summarization error: {str(e)}")
            return {
                "summary": "Unable to generate summary",
                "actions": [],
                "risks": [],
                "sentiment_overall": "neutral"
            }
    
    def enrich_utterances(self, utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich utterances with AI analysis
        """
        enriched = []
        
        for utterance in utterances:
            # Analyze sentiment
            sentiment_score = self.analyze_sentiment(utterance["content"])
            
            # Extract entities
            entities = self.extract_entities(utterance["content"])
            
            # Update utterance with enrichment data
            enriched_utterance = utterance.copy()
            enriched_utterance["sentiment_score"] = sentiment_score
            enriched_utterance["entities"] = entities
            
            # Try to identify department and region from entities
            if entities["organizations"]:
                # Simple mapping - in production, use proper entity mapping
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
