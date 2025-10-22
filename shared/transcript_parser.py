"""
Transcript parsing utilities for .vtt and .docx files
"""
import logging
import re
import uuid
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
import webvtt
from docx import Document


class TranscriptParser:
    """Parser for different transcript formats"""
    
    @staticmethod
    def time_to_seconds(time_str: str) -> float:
        """
        Convert time string (HH:MM:SS.mmm) to seconds
        """
        try:
            # Handle format like "00:00:01.000"
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds_parts = parts[2].split('.')
                seconds = int(seconds_parts[0])
                milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                
                total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
                return total_seconds
            return 0.0
        except:
            return 0.0
    
    @staticmethod
    def parse_vtt(file_content: str) -> List[Dict[str, Any]]:
        """
        Parse WebVTT transcript format
        Returns list of utterances with timestamps
        """
        utterances = []
        
        try:
            # Parse VTT content using webvtt library
            vtt = webvtt.from_string(file_content)
            
            for caption in vtt:
                # Extract speaker from caption text if it contains speaker info
                speaker = "Unknown Speaker"
                content = caption.text.strip()
                
                # Try to extract speaker from content (format: "Speaker: content")
                if ':' in content and len(content.split(':', 1)) == 2:
                    potential_speaker, potential_content = content.split(':', 1)
                    if len(potential_speaker.strip()) < 50:  # Reasonable speaker name length
                        speaker = potential_speaker.strip()
                        content = potential_content.strip()
                
                # Skip empty content
                if not content:
                    continue
                
                utterance = {
                    "utterance_id": str(uuid.uuid4()),
                    "speaker": speaker,
                    "content": content,
                    "start_time": caption.start,
                    "end_time": caption.end,
                    "duration": TranscriptParser.time_to_seconds(caption.end) - TranscriptParser.time_to_seconds(caption.start)
                }
                
                # Convert time strings to seconds for Azure AI Search
                utterance["start_time_seconds"] = TranscriptParser.time_to_seconds(caption.start)
                utterance["end_time_seconds"] = TranscriptParser.time_to_seconds(caption.end)
                
                utterances.append(utterance)
                
        except Exception as e:
            logging.error(f"Error parsing VTT content: {str(e)}")
            # Fallback to basic parsing if webvtt library fails
            utterances = TranscriptParser._parse_vtt_fallback(file_content)
        
        logging.info(f"Parsed {len(utterances)} utterances from VTT file")
        return utterances
    
    @staticmethod
    def _parse_vtt_fallback(file_content: str) -> List[Dict[str, Any]]:
        """
        Fallback VTT parsing using regex if webvtt library fails
        """
        utterances = []
        lines = file_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for timestamp lines (format: 00:00:01.000 --> 00:00:06.000)
            if '-->' in line and ':' in line:
                try:
                    start_time, end_time = line.split(' --> ')
                    start_time = start_time.strip()
                    end_time = end_time.strip()
                    
                    # Get the next non-empty line as content
                    i += 1
                    content = ""
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    
                    if i < len(lines):
                        content = lines[i].strip()
                        
                        # Extract speaker if content contains speaker info
                        speaker = "Unknown Speaker"
                        if ':' in content and len(content.split(':', 1)) == 2:
                            potential_speaker, potential_content = content.split(':', 1)
                            if len(potential_speaker.strip()) < 50:
                                speaker = potential_speaker.strip()
                                content = potential_content.strip()
                        
                        if content:
                            utterance = {
                                "utterance_id": str(uuid.uuid4()),
                                "speaker": speaker,
                                "content": content,
                                "start_time": start_time,
                                "end_time": end_time,
                                "duration": TranscriptParser.time_to_seconds(end_time) - TranscriptParser.time_to_seconds(start_time),
                                "start_time_seconds": TranscriptParser.time_to_seconds(start_time),
                                "end_time_seconds": TranscriptParser.time_to_seconds(end_time)
                            }
                            utterances.append(utterance)
                except Exception as e:
                    logging.warning(f"Error parsing VTT line: {line}, error: {str(e)}")
            
            i += 1
        
        logging.info(f"Fallback parsing extracted {len(utterances)} utterances")
        return utterances
    
    @staticmethod
    def parse_docx(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Parse Word document transcript format
        Returns list of utterances
        """
        utterances = []
        
        try:
            # Parse Word document
            doc = Document(io.BytesIO(file_content))
            
            current_speaker = None
            current_content = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                
                # Check if this looks like a speaker line
                speaker_match = re.match(r'^([^:]+):\s*(.+)$', text)
                
                if speaker_match:
                    # Save previous utterance if exists
                    if current_speaker and current_content:
                        utterance = {
                            "utterance_id": str(uuid.uuid4()),
                            "speaker": current_speaker,
                            "content": " ".join(current_content),
                            "start_time": None,  # No timestamps in Word docs
                            "end_time": None,
                            "duration": None
                        }
                        utterances.append(utterance)
                    
                    # Start new utterance
                    current_speaker = speaker_match.group(1).strip()
                    current_content = [speaker_match.group(2).strip()]
                else:
                    # Continue current utterance
                    if current_speaker:
                        current_content.append(text)
                    else:
                        # No speaker identified yet, treat as continuation
                        current_content.append(text)
            
            # Save last utterance
            if current_speaker and current_content:
                utterance = {
                    "utterance_id": str(uuid.uuid4()),
                    "speaker": current_speaker,
                    "content": " ".join(current_content),
                    "start_time": None,
                    "end_time": None,
                    "duration": None
                }
                utterances.append(utterance)
                
        except Exception as e:
            logging.error(f"Error parsing DOCX file: {str(e)}")
            raise ValueError(f"Invalid DOCX format: {str(e)}")
        
        return utterances
    
    @staticmethod
    def normalize_utterances(utterances: List[Dict[str, Any]], meeting_id: str, meeting_date: str = None) -> List[Dict[str, Any]]:
        """
        Normalize utterances for storage in Azure AI Search
        """
        normalized = []
        
        for utterance in utterances:
            # Convert time strings to seconds for Azure AI Search
            start_time_seconds = utterance.get("start_time_seconds", 0.0)
            end_time_seconds = utterance.get("end_time_seconds", 0.0)
            duration = utterance.get("duration", end_time_seconds - start_time_seconds)

            # Convert seconds to timestamp strings (HH:MM:SS format)
            start_timestamp = utterance.get("start_time", "00:00:00")
            end_timestamp = utterance.get("end_time", "00:00:00")

            current_time = datetime.utcnow().isoformat()
            
            # Use provided meeting_date or current time as fallback
            # Convert meeting_date to proper ISO format for Edm.DateTimeOffset
            if meeting_date:
                try:
                    # If it's just a date (YYYY-MM-DD), add time component
                    if len(meeting_date) == 10 and meeting_date.count('-') == 2:
                        meeting_date_value = f"{meeting_date}T00:00:00Z"
                    else:
                        meeting_date_value = meeting_date
                except:
                    meeting_date_value = current_time
            else:
                meeting_date_value = current_time

            normalized_utterance = {
                "id": utterance["utterance_id"],
                "meeting_id": meeting_id,
                "meeting_date": meeting_date_value,
                "speaker": utterance["speaker"],
                "department": "Unknown",  # Will be filled by AI enrichment
                "region": "Unknown",      # Will be filled by AI enrichment
                "topics": [],             # Will be filled by AI enrichment
                "sentiment_score": 0.0,   # Will be filled by AI enrichment
                "content": utterance["content"],
                "start_timestamp": start_timestamp if start_timestamp else "00:00:00",
                "end_timestamp": end_timestamp if end_timestamp else "00:00:00",
                "duration_seconds": float(duration) if duration else 0.0,
                "created_at": current_time,
                "updated_at": current_time
            }
            normalized.append(normalized_utterance)
        
        return normalized
