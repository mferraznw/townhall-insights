
import logging
import json
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from .config import config


class DataStorage:
    """Data storage manager for Azure services"""
    
    def __init__(self):
        # Initialize Azure AI Search client
        self.search_credential = AzureKeyCredential(config.azure_search_key)
        self.search_client = SearchClient(
            endpoint=config.azure_search_endpoint,
            index_name=config.azure_search_index_name,
            credential=self.search_credential
        )
        
        self.search_index_client = SearchIndexClient(
            endpoint=config.azure_search_endpoint,
            credential=self.search_credential
        )
        
        # Initialize Data Lake Storage client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            config.data_lake_connection_string
        )
    
    def create_search_index(self) -> bool:
        """
        Create the utterances search index with proper schema
        """
        try:
            index_definition = {
                "name": config.azure_search_index_name,
                "fields": [
                    {"name": "id", "type": "Edm.String", "key": True, "searchable": False, "filterable": True, "sortable": False, "facetable": False},
                    {"name": "meeting_id", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": False, "facetable": True},
                    {"name": "meeting_date", "type": "Edm.DateTimeOffset", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "speaker", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": False, "facetable": True},
                    {"name": "department", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": False, "facetable": True},
                    {"name": "region", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": False, "facetable": True},
                    {"name": "topics", "type": "Collection(Edm.String)", "searchable": True, "filterable": True, "sortable": False, "facetable": True},
                    {"name": "sentiment_score", "type": "Edm.Double", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "content", "type": "Edm.String", "searchable": True, "filterable": False, "sortable": False, "facetable": False},
                    {"name": "start_timestamp", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "end_timestamp", "type": "Edm.String", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "duration_seconds", "type": "Edm.Double", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "created_at", "type": "Edm.DateTimeOffset", "searchable": False, "filterable": True, "sortable": True, "facetable": False},
                    {"name": "updated_at", "type": "Edm.DateTimeOffset", "searchable": False, "filterable": True, "sortable": True, "facetable": False}
                ]
            }
            
            self.search_index_client.create_or_update_index(index_definition)
            logging.info(f"Search index '{config.azure_search_index_name}' created successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error creating search index: {str(e)}")
            return False
    
    def store_utterances(self, utterances: List[Dict[str, Any]]) -> bool:
        """Store utterances in Azure AI Search"""
        try:
            self.search_client.upload_documents(utterances)
            logging.info(f"Stored {len(utterances)} utterances in search index")
            return True
        except Exception as e:
            logging.error(f"Error storing utterances: {str(e)}")
            return False
    
    def search_utterances(self, search_text: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, top: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Search utterances with filters and pagination"""
        try:
            search_params = {"top": top, "skip": skip, "include_total_count": True}
            
            if search_text:
                search_params["search_text"] = search_text
            
            if filters:
                filter_parts = []
                if "from_date" in filters:
                    filter_parts.append(f"meeting_date ge {filters['from_date']}")
                if "to_date" in filters:
                    filter_parts.append(f"meeting_date le {filters['to_date']}")
                if "speaker" in filters:
                    filter_parts.append(f"speaker eq '{filters['speaker']}'")
                if "department" in filters:
                    filter_parts.append(f"department eq '{filters['department']}'")
                if "region" in filters:
                    filter_parts.append(f"region eq '{filters['region']}'")
                if "topics" in filters:
                    topic_filters = [f"topics/any(t: t eq '{topic}')" for topic in filters["topics"]]
                    filter_parts.append(f"({' or '.join(topic_filters)})")
                if "sentiment_min" in filters:
                    filter_parts.append(f"sentiment_score ge {filters['sentiment_min']}")
                if "sentiment_max" in filters:
                    filter_parts.append(f"sentiment_score le {filters['sentiment_max']}")
                
                if filter_parts:
                    search_params["filter"] = " and ".join(filter_parts)
            
            results = self.search_client.search(**search_params)
            return list(results)
            
        except Exception as e:
            logging.error(f"Error searching utterances: {str(e)}")
            return []
    
    def store_transcript(self, meeting_id: str, transcript_content: str, file_format: str) -> bool:
        """Store raw transcript in Data Lake Storage"""
        try:
            container_name = "transcripts"
            blob_name = f"{meeting_id}/transcript.{file_format}"
            
            try:
                self.blob_service_client.create_container(container_name)
            except:
                pass
            
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.upload_blob(transcript_content, overwrite=True)
            logging.info(f"Stored transcript for meeting {meeting_id} in Data Lake")
            return True
            
        except Exception as e:
            logging.error(f"Error storing transcript: {str(e)}")
            return False
    
    def get_transcript(self, meeting_id: str, file_format: str) -> Optional[str]:
        """Retrieve transcript from Data Lake Storage"""
        try:
            container_name = "transcripts"
            blob_name = f"{meeting_id}/transcript.{file_format}"
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            content = blob_client.download_blob().readall().decode('utf-8')
            return content
        except Exception as e:
            logging.error(f"Error retrieving transcript: {str(e)}")
            return None
    
    def get_trends(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculate trends from stored utterances"""
        try:
            utterances = self.search_utterances(filters=filters, top=1000)
            topic_counts = {}
            sentiment_by_topic = {}
            
            for utterance in utterances:
                topics = utterance.get("topics", [])
                sentiment = utterance.get("sentiment_score", 0.0)
                
                for topic in topics:
                    if topic not in topic_counts:
                        topic_counts[topic] = 0
                        sentiment_by_topic[topic] = []
                    topic_counts[topic] += 1
                    sentiment_by_topic[topic].append(sentiment)
            
            trends = []
            for topic, count in topic_counts.items():
                avg_sentiment = sum(sentiment_by_topic[topic]) / len(sentiment_by_topic[topic])
                trend = {
                    "name": topic.replace("_", " ").title(),
                    "description": f"Discussion about {topic.replace('_', ' ')}",
                    "meetings_count": count,
                    "avg_sentiment": round(avg_sentiment, 2),
                    "momentum": "up" if avg_sentiment > 0.1 else "down" if avg_sentiment < -0.1 else "flat",
                    "novelty_score": min(count / 10.0, 1.0),
                    "support": []
                }
                trends.append(trend)
            
            return {
                "window_start": filters.get("from_date") if filters else "2025-01-01",
                "window_end": filters.get("to_date") if filters else "2025-12-31",
                "trends": sorted(trends, key=lambda x: x["meetings_count"], reverse=True)[:10]
            }
            
        except Exception as e:
            logging.error(f"Error calculating trends: {str(e)}")
            return {"window_start": "", "window_end": "", "trends": []}
