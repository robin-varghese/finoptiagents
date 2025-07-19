# First, ensure you are in the directory where your 'tools.yaml' file is located
# For example:
# cd /path/to/your/project/containing/tools.yaml

# Set the version environment variable (if you haven't already in this terminal session)
export VERSION=0.5.0

docker run \
  -p 5001:5000 \
  -v "$(pwd)/tools.yaml:/app/tools.yaml" \
  us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:0.5.0 \
  --tools-file "/app/tools.yaml"\
