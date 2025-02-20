exec uvicorn api.main:create_app \
    --host 0.0.0.0 \
    --port 8080 \
    --factory \
    --log-level debug \
    --no-access-log \
    --reload \
    --timeout-keep-alive 75 