# Pull base image
FROM python:3.7
# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /code/
# Install dependencies
COPY requirements.txt /code/
RUN pip install -r /code/requirements.txt
COPY . /code/
EXPOSE 19093
CMD ["python", "main.py"]
