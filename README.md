# AI Student Query Assistant

A desktop application that uses Google's Gemini API to answer student questions with a user-friendly interface.

## Features

- Simple, intuitive chat interface
- AI-powered responses using Google Gemini models
- Local caching of responses for faster repeat inquiries
- Cross-platform desktop application built with Tkinter

## Prerequisites

- Python 3.7 or higher
- Google Gemini API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/dhairyak56/ai-student-query-assistant.git
   cd ai-student-query-assistant
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root directory with your API key:
   ```
   GEMINI_API_KEY=your_actual_api_key
   ```

## Usage

1. Start the backend API:
   ```
   python backend_api.py
   ```

2. In a separate terminal, start the desktop application:
   ```
   python ai_student_query_assistant.py
   ```

3. Type your questions in the input field and press Enter or click Send to get answers.

## Troubleshooting

If you encounter issues, run the troubleshooting script:
```
python troubleshoot.py
```

## Database Management

The application caches responses in a local SQLite database. You can:
- View statistics via the Tools menu
- Clear the cache via the Tools menu

## Configuration

Settings can be accessed from the File menu to configure:
- API connection details
- Database caching options
- UI preferences


## Acknowledgments

- This project uses Google's Gemini API for generating responses
