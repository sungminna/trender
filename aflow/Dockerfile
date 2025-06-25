FROM apache/airflow:3.0.2

# Switch to root to install system packages
USER root

# Playwright 브라우저 실행에 필요한 시스템 패키지
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libxkbcommon-x11-0 \
    libdrm2 \
    libgbm1 \
    libxcb1 \
    xdg-utils \
    libasound2 \
    libdbus-glib-1-2 \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user
USER airflow

COPY requirements.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# Switch back to root to install playwright browsers
USER root
RUN su airflow -c "playwright install"
RUN playwright install-deps

# Switch back to airflow user for runtime
USER airflow