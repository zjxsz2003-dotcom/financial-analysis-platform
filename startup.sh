#!/bin/bash
set -e
apt-get update -qq && apt-get install -y -qq wget unzip > /dev/null 2>&1
pip install -q streamlit pandas plotly openpyxl fpdf2 openai numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
wget -q -O /tmp/app.zip https://gitee.com/zoujiaxin2003/financial-analysis-platform/repository/archive/master.zip
cd /tmp
unzip -q app.zip
DIRNAME=$(ls -d */ | grep zoujiaxin | head -1)
cd "$DIRNAME"
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml << EOF
[server]
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = false
headless = true
EOF
exec streamlit run app.py
