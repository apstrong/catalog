# Omni Catalog

A Streamlit web application for browsing and viewing model configurations from the Omni API.

## Features

- Automatic loading of available models
- Interactive model selection
- YAML file viewing with syntax highlighting
- Clean and intuitive user interface

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd omni-catalog
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with your API credentials:
```
OMNI_API_KEY=your_api_key_here
```

5. Run the application:
```bash
streamlit run app.py
```

## Requirements

- Python 3.9+
- Streamlit
- PyYAML
- python-dotenv 