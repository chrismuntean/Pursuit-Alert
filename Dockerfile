# Stage 1: Build stage for installing dependencies
FROM python:3.9-alpine AS build-env

# Install build dependencies
RUN apk add --no-cache build-base libpng-dev openblas-dev && \
    apk add --no-cache --virtual .build-deps gcc musl-dev jpeg-dev zlib-dev

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage for running the application
FROM python:3.9-alpine AS runtime

# Install runtime dependencies
RUN apk add --no-cache libpng openblas && \
    apk add --no-cache jpeg-dev zlib-dev

WORKDIR /usr/src/app

COPY --from=build-env /usr/local /usr/local
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "Pursuit_Alert.py"]