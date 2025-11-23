@echo off
echo Starting Route Optimization Visualizer
echo =====================================

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Run Streamlit app
echo Starting Streamlit app...
echo The app will open in your browser at http://localhost:8501
streamlit run app.py

pause