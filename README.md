# Pinecone Client

A web application for searching documents using Pinecone vector database with support for reranking models.

<img width="1226" alt="image" src="https://github.com/user-attachments/assets/a3f93db4-2b8e-438e-908a-1fe2057090cb" />


## Features

- Search documents using Pinecone vector database
- Select different indexes and namespaces
- Rerank search results using various models
- Configure the number of search results
- View detailed search configuration and usage information

## Project Structure

```
.
├── app/                  # Main application directory
│   ├── app.py            # Main application file
│   ├── server.py         # Server logic and API routes
│   └── templates/        # HTML templates
│       └── base.html     # Main HTML template
├── scripts/              # Utility scripts
│   ├── analyze_verkada_docs.py
│   ├── analyze_verkada_docs_simple.py
│   ├── clean_json.py
│   ├── pinecone_upsert.py
│   ├── pinecone_verkada_upsert.py
│   ├── scraper.py
│   └── transform_verkada_docs.py
├── .env                  # Environment variables (not tracked in git)
├── .gitignore            # Git ignore file
├── requirements.txt      # Python dependencies (Flask, Pinecone, python-dotenv)
├── run.py                # Entry point to run the application
└── README.md             # This file
```

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your Pinecone API key:
   ```
   PINECONE_API_KEY=your_api_key_here
   ```
5. Create a `data` directory for your data files (this directory is excluded from git):
   ```
   mkdir -p data
   ```

## Running the Application

1. Activate the virtual environment if not already activated:
   ```
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Run the application:
   ```
   python run.py
   ```
3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Select an index and namespace from the dropdown menus
2. Optionally select a reranking model and specify the number of results
3. Enter your search query in the search box and press Enter
4. View the search results with their relevance scores
5. Click on a result to expand and view the full content

## Utility Scripts

The `scripts` directory contains various utility scripts for:
- Analyzing documents
- Transforming data
- Uploading data to Pinecone
- Web scraping

Refer to each script's documentation for usage details. 
