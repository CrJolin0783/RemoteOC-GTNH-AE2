FROM python:3.10-slim

RUN apt-get install ca-certificates

# Copy the current directory contents into the container at /app
COPY . /app

# Set the working directory
WORKDIR /app

# 安装依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
&& pip config set global.trusted-host mirrors.aliyun.com \
&& pip install --upgrade pip \
&& pip install -r requirements.txt --no-warn-script-location

EXPOSE 8080

CMD ["python3", "run.py", "--port", "1030"]
#CMD ["python3", "-m", "uvicorn", "run:app", "--host", "0.0.0.0", "--port ", "80"]