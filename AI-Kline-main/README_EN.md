# AI Stock Analysis - A-share Technical Analysis and AI Prediction Tool

## Project Overview

AI Stock Analysis is a Python-based A-share analysis tool that combines traditional technical analysis with AI prediction capabilities. It provides comprehensive stock analysis and forecasting using K-line charts, technical indicators, financial data, and news data. The tool can:

1. Retrieve historical price-volume data for A-share stocks and calculate various technical indicators
2. Generate professional K-line charts and technical indicator visualizations
3. Access stock-related financial data and news information
4. Use  multi-modal AI model to analyze integrated data and predict future stock trends

## Key Features

- **Data Acquisition**: Uses AKShare to obtain historical trading data, financial data, and news for A-share stocks
- **Technical Analysis**: Calculates multiple technical indicators including MA, MACD, KDJ, RSI, Bollinger Bands, etc.
- **Visualization**: Generates static and interactive K-line charts and technical indicator charts
- **AI Analysis**: Utilizes  multi-modal AI model to analyze stock data and predict future trends
- **Web Interface**: Provides a clean and intuitive web interface for users to input stock codes and view analysis results
- **MCP SERVER**: Offers MCP SERVER support for LLM interaction, enabling real-time stock analysis

## Installation Guide

### Requirements

- Python 3.8+
- Dependencies: See `requirements.txt`

### Installation Steps

1. Clone or download this project locally

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file and add API key:
```
API_KEY=your_api_key_here
BASE_URL==https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-vl-max
```

> Note: You need to use multi-modal models

## Usage

### Command Line Usage
```bash
python main.py --stock_code 000001 --period 1year --save_path ./output
```

Parameters:
- `--stock_code`: Stock code (required)
- `--period`: Analysis period, options: "1year", "6months", "3months", "1month" (default: "1year")
- `--save_path`: Result save path (default: "./output")

### Web Interface Usage

Start web service:
```bash
python web_app.py
```

Then access http://localhost:5000 in your browser:

1. Enter stock code in the form (e.g.: 000001)
2. Select analysis period
3. Click "Start Analysis" button
4. View results after analysis completes

Web interface includes:
- Basic stock information
- K-line charts and technical indicator charts
- AI analysis results text

Screenshot:
![Web Interface Screenshot](static/images/image.png)

### MCP SERVER Usage

Start MCP server:
```bash
uv run mcp_server.py
```

Then configure in MCP client (streamable-http):
http://localhost:8000/mcp

Cherry-Studio Screenshots:
![MCP Interface Screenshot](static/images/mcp1.png)
![MCP Interface Screenshot](static/images/mcp2.png)

### Output Results

After execution, the program will generate in specified save path:
1. K-line charts and technical indicator charts (static PNG and interactive HTML)
2. AI analysis result text files

## Project Structure
```
AI Stock Analysis/
├── main.py                 # Main program entry
├── web_app.py              # Web application entry
├── requirements.txt        # Dependency list
├── .env                    # Environment variables (create manually)
├── modules/                # Functional modules
│   ├── __init__.py
│   ├── data_fetcher.py     # Data fetching module
│   ├── technical_analyzer.py # Technical analysis module
│   ├── visualizer.py       # Visualization module
│   └── ai_analyzer.py      # AI analysis module
├── templates/              # Web templates
│   └── index.html          # Main template
├── static/                 # Static resources
│   ├── css/                # CSS styles
│   │   └── style.css       # Custom styles
│   └── js/                 # JavaScript
│       └── main.js         # Main script
└── output/                 # Output directory (created at runtime)
    ├── charts/             # Charts directory
    └── *_analysis_result.txt # Analysis result files
```


## Notes
- This tool is for learning and research purposes only, not investment advice
- AI analysis results are based on historical data and current information, with no guarantee of future accuracy
- Ensure Gemini API key is properly configured before use
- Stock data retrieval depends on AKShare library and may be limited by network/data source availability
- This is a QuantML open-source project. Please credit source for redistribution. Contact WeChat ID QuantML for commercial use.

## Disclaimer
The analysis and predictions provided by this tool are for reference only and do not constitute investment advice. Investing carries risks. Users are responsible for their own investment decisions.
