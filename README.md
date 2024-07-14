1. Set credentials in env , do NOT  change the name of the db , just host/user/pass and api_key.
2. Edit the domain name in postfix/conf - main.cf, master.cf, virtual, transport.
3. Run docker-compose up -d
4. Send email to anything@domain.
5. http://domain:5000/emails?to_email=name@domain.com&api_key=test

<p class="has-line-data" data-line-start="0" data-line-end="3">API Documentation<br>
Authentication<br>
All endpoints require an api_key parameter to be passed in the URL.</p>
<p class="has-line-data" data-line-start="4" data-line-end="5">Endpoints</p>
<ol>
<li class="has-line-data" data-line-start="5" data-line-end="22">
<p class="has-line-data" data-line-start="5" data-line-end="21">Get Emails<br>
URL: /emails<br>
Method: GET<br>
Parameters:<br>
to_email (required): The email address to filter emails by.<br>
sort (optional): Sort order (ASC or DESC). Default is DESC.<br>
limit (optional): Limit the number of emails returned.<br>
offset (optional): Skip a number of emails.<br>
api_key (required): Your secret API key.<br>
Response:<br>
count: Number of emails that matched the query.<br>
limit: Number of emails returned in this request.<br>
offset: Number of emails skipped.<br>
emails: List of emails.<br>
Example:<br>
curl &quot;<a href="http://localhost:5000/emails?to_email=test@example.com&amp;api_key=YourSecretApiKey">http://localhost:5000/emails?to_email=test@example.com&amp;api_key=YourSecretApiKey</a>&quot;</p>
</li>
<li class="has-line-data" data-line-start="22" data-line-end="31">
<p class="has-line-data" data-line-start="22" data-line-end="30">Delete an Email<br>
URL: /emails/&lt;int:email_id&gt;<br>
Method: DELETE<br>
Parameters:<br>
api_key (required): Your secret API key.<br>
Response: Message indicating the success of the operation.<br>
Example:<br>
curl -X DELETE &quot;<a href="http://localhost:5000/emails/1?api_key=YourSecretApiKey">http://localhost:5000/emails/1?api_key=YourSecretApiKey</a>&quot;</p>
</li>
<li class="has-line-data" data-line-start="31" data-line-end="40">
<p class="has-line-data" data-line-start="31" data-line-end="39">Delete All Emails<br>
URL: /emails<br>
Method: DELETE<br>
Parameters:<br>
api_key (required): Your secret API key.<br>
Response: Message indicating the success of the operation.<br>
Example:<br>
curl -X DELETE &quot;<a href="http://localhost:5000/emails?api_key=YourSecretApiKey">http://localhost:5000/emails?api_key=YourSecretApiKey</a>&quot;</p>
</li>
<li class="has-line-data" data-line-start="40" data-line-end="51">
<p class="has-line-data" data-line-start="40" data-line-end="50">Get Email Stats<br>
URL: /emails/stats<br>
Method: GET<br>
Parameters:<br>
api_key (required): Your secret API key.<br>
Response:<br>
total_email_count: Total number of emails in the database.<br>
database_size_mb: Size of the database in MB.<br>
Example:<br>
curl &quot;<a href="http://localhost:5000/emails/stats?api_key=YourSecretApiKey">http://localhost:5000/emails/stats?api_key=YourSecretApiKey</a>&quot;</p>
</li>
</ol>
<p class="has-line-data" data-line-start="51" data-line-end="53">Security<br>
To secure the API:</p>
<p class="has-line-data" data-line-start="54" data-line-end="57">Use a strong, unique API_KEY.<br>
Implement HTTPS to encrypt data between clients and the server.<br>
Restrict access to the API by IP address if possible.</p>

## TO DO ##
Avoid using it on prod, API KEY  in URL is far away from best practise , better to be in header.
Also use nginx as reverse proxy for examle but not open port 5000 outside.
