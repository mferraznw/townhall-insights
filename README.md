# Townhall Insights Function App

Azure Functions-based API for analyzing townhall meeting transcripts using AI services.

## Features

- **File Upload**: Upload .vtt and .docx transcript files
- **Microsoft Graph Integration**: Automatic ingestion of Teams meeting transcripts
- **AI Enrichment**: Sentiment analysis, topic clustering, and entity extraction
- **Search & Analytics**: Query utterances, trends, and speaker insights
- **Authentication**: Entra ID OAuth2 integration

## Endpoints

### Upload
- `POST /upload` - Upload transcript files (.vtt, .docx)

### Insights
- `GET /insights/trends` - Get trending topics and sentiment analysis
- `GET /insights/speakers` - Get speaker analysis and sentiment
- `GET /insights/utterances` - Search utterances with filtering

### Webhooks
- `GET/POST /hooks/graph` - Microsoft Graph webhook for Teams integration

## Configuration

Update `local.settings.json` with your Azure service endpoints:

```json
{
  "AZURE_SEARCH_ENDPOINT": "https://your-search.search.windows.net",
  "AZURE_SEARCH_KEY": "your-search-key",
  "AZURE_OPENAI_ENDPOINT": "https://your-openai.openai.azure.com/",
  "AZURE_OPENAI_API_KEY": "your-openai-key",
  "AZURE_AI_LANGUAGE_ENDPOINT": "https://your-language.cognitiveservices.azure.com/",
  "AZURE_AI_LANGUAGE_KEY": "your-language-key"
}
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the function app:
```bash
func start
```

## Deployment

1. Deploy Azure infrastructure:
```bash
az deployment group create --resource-group your-rg --template-file ../docs/azure_deploy.bicep --parameters @../docs/azure_deploy.parameters.json
```

2. Deploy function app:
```bash
func azure functionapp publish your-function-app-name --python
```

## Authentication

All endpoints require Entra ID authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <your-access-token>
```

## API Documentation

See `../insights-api-swagger2.yaml` for complete API documentation compatible with Copilot Studio.
