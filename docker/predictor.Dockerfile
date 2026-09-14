FROM python:3.12-slim
WORKDIR /app

# Install deps first for layer caching -- code changes shouldn't re-trigger a full torch reinstall
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# processed_data (model checkpoint, graph, cleaned data) is mounted in at
# runtime via the shared volume -- it's generated locally and too large/
# dynamic to bake into the image. See docker-compose.yml.
# WORKDIR stays /app (not /app/src) so the script's relative
# "processed_data/..." paths resolve the same way they do when you run it
# locally from the project root.
ENTRYPOINT ["python", "src/export_predictions.py"]
