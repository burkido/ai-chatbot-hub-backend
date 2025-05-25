# Multilingual Support

This document describes how to use the multilingual features of the Doctor AI API.

## Supported Languages

The API supports the following languages:

- Arabic (ar)
- German (de)
- English (en) - default
- Spanish (es)
- French (fr)
- Hindi (hi)
- Italian (it)
- Japanese (ja)
- Korean (ko)
- Portuguese (pt)
- Russian (ru)
- Turkish (tr)
- Chinese (zh)

## Using Languages in API Calls

You can specify the language for responses in three ways (in order of precedence):

1. In the request body of the chat endpoint with the `language` field:
   ```json
   {
     "message": "My stomach hurts",
     "history": [],
     "topic": "General",
     "namespace": "medical",
     "language": "es"  // Response will be in Spanish
   }
   ```

2. In the query string:
   ```
   /api/v1/chat?language=fr  // Response will be in French
   ```

3. Using the Accept-Language HTTP header:
   ```
   Accept-Language: de  // Response will be in German if no other language is specified
   ```

## Implementation Details

The translation process works as follows:

1. The user's message is received in their language
2. The message is translated to English for processing with our medical knowledge base
3. The response is generated in English
4. The response is translated back to the user's preferred language

This approach ensures that our medical knowledge base can be efficiently queried in English while providing responses in the user's preferred language.

## Advanced Features

The translation service supports several advanced features:

- **Language Detection**: Automatically detects the language of user input
- **Batch Translation**: Efficiently translates multiple texts in a single request
- **HTML Content**: Supports translation of HTML content with proper tag handling
- **V3 API Support**: When configured with a Google Project ID, uses the more advanced V3 API

## Configuration

To use the translation service, you need to set the following environment variables:

- `GOOGLE_TRANSLATE_API_KEY`: Your Google Cloud API key with Translation API enabled
- `GOOGLE_PROJECT_ID`: (Optional) Your Google Cloud project ID to use the V3 API

## Credit Costs

Using translation adds 1 credit to the cost of each chat message for non-premium users:
- Chat without translation: 1 credit (2 credits if medical sources are returned)
- Chat with translation: 2 credits (3 credits if medical sources are returned)

## Error Handling

If an unsupported language code is provided, the system will fall back to English as the default language.

The translation service includes retry logic for transient errors, automatically retrying failed requests up to 3 times with exponential backoff.
