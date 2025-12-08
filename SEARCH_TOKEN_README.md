# Search Token Implementation for DoS Protection

## Overview

This implementation adds a one-time token system for the search API to help prevent DoS (Denial of Service) attacks. Users must obtain a valid token before performing a search, and each token can only be used once.

## Features

- **One-time tokens**: Each search token can only be used once
- **Time-limited**: Tokens expire after 5 minutes
- **Automatic cleanup**: Old tokens are automatically cleaned up (older than 1 hour)
- **Transparent to users**: The frontend automatically fetches and uses tokens

## Changes Made

### 1. Backend Changes

#### New Model: `SearchToken` (app/models/utils.py)
- Stores one-time search tokens
- Fields: token, created_at, used, ip_address
- Methods:
  - `generate()`: Creates a new search token
  - `validate_and_use()`: Validates and marks a token as used
  - `cleanup_old_tokens()`: Removes tokens older than 1 hour

#### New API Endpoint (app/views/api.py)
- `GET /api/search/token`: Returns a new one-time search token
- No authentication required
- Includes automatic periodic cleanup of old tokens

#### Modified Search Endpoints (app/views/home.py)
- `/search/`: Now requires a valid token parameter
- `/search-reviews/`: Now requires a valid token parameter
- Returns 403 error if token is invalid or missing

### 2. Frontend Changes

#### Search Form (app/templates/layout.html)
- Intercepts search form submission
- Automatically fetches a token before performing search
- Includes token in the search URL

#### Search Results Pagination (app/templates/search.html, search-reviews.html)
- Pagination links automatically fetch new tokens
- Ensures seamless navigation through search results

## Installation

### 1. Database Migration

Run the SQL migration script to create the search_tokens table:

```bash
mysql -u your_username -p your_database < migrations_search_token.sql
```

Or using Flask-Migrate (if configured):

```bash
flask db migrate -m "Add search_tokens table"
flask db upgrade
```

### 2. Deploy Code

Deploy the updated code to your server.

### 3. Test

Test the search functionality to ensure tokens are being generated and validated correctly.

## Configuration

No additional configuration is required. The system uses the following defaults:

- Token expiration: 5 minutes
- Token cleanup: Tokens older than 1 hour are removed
- Token length: 32 bytes (urlsafe base64 encoded)

## Security Considerations

1. **Rate Limiting**: Consider adding rate limiting to the `/api/search/token` endpoint to prevent token generation abuse
2. **IP Tracking**: The system tracks IP addresses to help identify potential abuse patterns
3. **Monitoring**: Monitor the search_tokens table size to ensure cleanup is working properly

## Troubleshooting

### Users can't perform searches
- Check that the `search_tokens` table exists
- Verify that the `/api/search/token` endpoint is accessible
- Check browser console for JavaScript errors

### Table growing too large
- Verify that the cleanup function is running
- Manually run: `DELETE FROM search_tokens WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);`

### 403 Errors on search
- Tokens may be expiring too quickly if there's clock skew
- Users may have JavaScript disabled (tokens require JavaScript)
- Check that tokens are being generated correctly

## Future Enhancements

Consider implementing:
- Rate limiting on token generation per IP
- CAPTCHA for suspicious IPs
- Metrics/monitoring for token usage
- Admin dashboard to monitor search API usage

