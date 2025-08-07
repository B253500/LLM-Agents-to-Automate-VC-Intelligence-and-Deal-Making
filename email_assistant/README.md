# Q&A Email Assistant

This service listens for incoming emails, analyzes the questions they contain, and provides answers. It is designed to be triggered by a dedicated n8n workflow that is connected to an email account.

### Key Components
-   **API Server**: `api_server.py` (runs on port 5001)
-   **Endpoint**: `/analyze`
-   **Core Logic**: `agents/vc_report_agent.py`
-   **n8n Workflow**: A workflow on your n8n instance (like `n8n_workflow.json`) configured with an email trigger.

### Setup Guide for Q&A Assistant

#### Step 1: Install Dependencies
Make sure you have activated your Python virtual environment and installed the necessary packages.
```bash
# Activate your virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

#### Step 2: Configure Environment Variables
The assistant requires an OpenAI API key to function. Create or update your `.env` file in the project root and add your key:
```
OPENAI_API_KEY=sk-your-openai-api-key-here
```

#### Step 3: Run the API Server
Start the dedicated server for the Q&A assistant.
```bash
python email_assistant/api_server.py
```
The server will start on `http://0.0.0.0:5001`.

#### Step 4: Configure the n8n Workflow
1.  Log in to your n8n instance on Noumena.
2.  Create a new workflow.
3.  **Set up the Trigger**: Use an "Email Read" or similar trigger node and configure it to connect to your desired email account. Set it to trigger whenever a new email arrives.
4.  **Call the API**: Add an "HTTP Request" node to call the `/analyze` endpoint of your API server.
    -   **URL**: `http://<your_server_ip>:5001/analyze` (replace `<your_server_ip>` with the public IP of your Noumena server).
    -   **Method**: `POST`
    -   **Body**: Send a JSON object containing the question and email ID from the email trigger step.
        ```json
        {
          "question": "{{$json.body.text}}",
          "email_id": "{{$json.id}}"
        }
        ```
5.  **Send Reply Email**: Add an "Email Send" node to send the answer received from the API back to the original sender.

### How It Works
1.  An email is received in the monitored inbox.
2.  The n8n workflow triggers and extracts the email content.
3.  n8n sends the content to the `/analyze` endpoint.
4.  The Flask server uses the `VCReportAgent` to generate an answer.
5.  n8n receives the answer and sends a reply email.
