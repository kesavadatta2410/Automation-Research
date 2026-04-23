api: uvicorn backend.main:app --host 0.0.0.0 --port 8000
web: streamlit run app.py --server.port $PORT --server.headless true
scheduler: python services/scheduler.py
