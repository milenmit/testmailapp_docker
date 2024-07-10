API Documentation
Authentication
All endpoints require an api_key parameter to be passed in the URL.

Endpoints
1. Get Emails
URL: /emails
Method: GET
Parameters:
to_email (required): The email address to filter emails by.
sort (optional): Sort order (ASC or DESC). Default is DESC.
limit (optional): Limit the number of emails returned.
offset (optional): Skip a number of emails.
api_key (required): Your secret API key.
Response:
count: Number of emails that matched the query.
limit: Number of emails returned in this request.
offset: Number of emails skipped.
emails: List of emails.
Example:

curl "http://localhost:5000/emails?to_email=test@example.com&api_key=YourSecretApiKey"
2. Delete an Email
URL: /emails/<int:email_id>
Method: DELETE
Parameters:
api_key (required): Your secret API key.
Response: Message indicating the success of the operation.
Example:

curl -X DELETE "http://localhost:5000/emails/1?api_key=YourSecretApiKey"
3. Delete All Emails
URL: /emails
Method: DELETE
Parameters:
api_key (required): Your secret API key.
Response: Message indicating the success of the operation.
Example:


curl -X DELETE "http://localhost:5000/emails?api_key=YourSecretApiKey"
4. Get Email Stats
URL: /emails/stats
Method: GET
Parameters:
api_key (required): Your secret API key.
Response:
total_email_count: Total number of emails in the database.
database_size_mb: Size of the database in MB.
Example:


curl "http://localhost:5000/emails/stats?api_key=YourSecretApiKey"
Security
To secure the API:

Use a strong, unique API_KEY.
Implement HTTPS to encrypt data between clients and the server.
Restrict access to the API by IP address if possible.
