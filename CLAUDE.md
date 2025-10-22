# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Azure Functions-based API for analyzing townhall meeting transcripts using AI services. The system ingests transcripts (.vtt or .docx files), enriches them with AI-powered sentiment analysis, topic clustering, and entity extraction, then stores the data in Azure AI Search for querying and analytics.

## Local Development

### Start Function App
```bash
func start
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Configuration

All Azure service credentials are managed through `shared/config.py`, which supports both environment variables and Azure Key Vault. Required configuration in `local.settings.json`:

- `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_KEY` - Azure AI Search service
- `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` - Azure OpenAI for embeddings and summarization
- `AZURE_AI_LANGUAGE_ENDPOINT` / `AZURE_AI_LANGUAGE_KEY` - Azure AI Language for sentiment/entity analysis (optional)
- `AZURE_STORAGE_CONNECTION_STRING` - Blob storage for raw transcripts
- `DATA_LAKE_CONNECTION_STRING` - Data Lake storage
- `TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` - Entra ID authentication

## Architecture

### Core Processing Pipeline

The transcript processing flow follows this sequence:

1. **Ingestion** (`upload/__init__.py` or `hooks/graph/__init__.py`)
   - Upload endpoint accepts .vtt (WebVTT) or .docx files
   - Graph webhook endpoint receives notifications for Teams meetings

2. **Parsing** (`shared/transcript_parser.py`)
   - `TranscriptParser.parse_vtt()` - Parses WebVTT format with timestamps
   - `TranscriptParser.parse_docx()` - Extracts speaker:text patterns from Word docs
   - `TranscriptParser.normalize_utterances()` - Converts to standardized format for Azure AI Search

3. **AI Enrichment** (`shared/ai_enrichment.py`)
   - `AIEnrichment.analyze_sentiment()` - Azure AI Language sentiment scoring (-1 to 1)
   - `AIEnrichment.extract_entities()` - Extracts persons, organizations, locations
   - `AIEnrichment.generate_topics()` - Keyword-based topic detection (sugar_reduction, packaging, sustainability, etc.)
   - `AIEnrichment.summarize_meeting()` - GPT-4 powered meeting summary with actions/risks
   - `AIEnrichment.enrich_utterances()` - Orchestrates all enrichment steps, infers department/region from entities

4. **Storage** (`shared/data_storage.py`)
   - Raw transcripts stored in Data Lake Storage (Blob containers)
   - Enriched utterances indexed in Azure AI Search with schema defined in `DataStorage.create_search_index()`
   - Search supports filtering by date, speaker, department, region, topics, sentiment

### Azure AI Search Schema

Key fields in the utterances index:
- `id` (key), `meeting_id`, `meeting_date`, `speaker`
- `department`, `region` - Inferred from entity extraction
- `topics` - Collection(Edm.String) for keyword-based topics
- `sentiment_score` - Edm.Double from -1 (negative) to 1 (positive)
- `content` - Searchable transcript text
- `start_timestamp`, `end_timestamp`, `duration_seconds` - Timing info (VTT only)

### Azure Function Endpoints

HTTP routes defined in `function.json` files:

- `POST /upload` - Upload .vtt/.docx files
- `GET /insights/trends` - Aggregated topic trends with sentiment (uses `DataStorage.get_trends()`)
- `GET /insights/speakers` - Speaker-level analytics
- `GET /insights/utterances` - Search utterances with filters (date, speaker, department, region, topics, sentiment range)
- `GET/POST /hooks/graph` - Microsoft Graph webhook for Teams integration

Authentication handled by `shared/auth.py` with Entra ID OAuth2 (currently disabled in upload endpoint for testing).

### Microsoft Graph Integration

The `hooks/graph/__init__.py` webhook:
1. Handles validation (GET with validationToken)
2. Processes notifications (POST) to extract meeting transcripts
3. Uses `ConfidentialClientApplication` from MSAL to acquire Graph API tokens
4. Fetches transcripts from `/communications/onlineMeetings/{id}/recordings`
5. Processes transcripts through the same enrichment pipeline

## Key Implementation Details

### Sentiment Scoring
Azure AI Language returns confidence scores for positive/negative/neutral. The system converts this to a single score:
- Positive: returns positive confidence (0 to 1)
- Negative: returns negative confidence as negative value (-1 to 0)
- Neutral: returns 0.0

### Topic Detection
Currently uses keyword matching against predefined topics in `ai_enrichment.py`:
- sugar_reduction, packaging, sustainability, market_trends, operations, innovation
- Falls back to "general_discussion" if no keywords match
- Topics are applied to all utterances in a meeting (not per-utterance)

### Field Name Inconsistencies
Note: There are field name inconsistencies between parsing and storage:
- Parser uses `"content"` for utterance text
- Search index schema expects `"text"` field
- Upload endpoint uses `"text"` when generating topics (line 81)
- This may cause issues and should be standardized

### Error Handling
AI enrichment has fallback logic in `upload/__init__.py` (lines 74-96) - if enrichment fails, the system stores utterances with default values rather than failing the upload.

## Deployment

Deploy Azure infrastructure:
```bash
az deployment group create --resource-group your-rg --template-file ../docs/azure_deploy.bicep --parameters @../docs/azure_deploy.parameters.json
```

Deploy function app:
```bash
func azure functionapp publish your-function-app-name --python
```

Function timeout configured to 10 minutes in `host.json`.
