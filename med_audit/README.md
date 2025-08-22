# My Eye Dr Audit

Containerized My Eye Dr audit to run automatically weekly.

# Images will be in the artifact registry under:
us-east4-docker.pkg.dev/rugged-night-193017/scheduled-jobs

# Build the container. Run this command from the folder that has the Dockerfile
docker build -t med_audit .

# Tag the already built image
docker tag med_audit us-east4-docker.pkg.dev/rugged-night-193017/scheduled-jobs/med_audit:latest

# Push the image to the artifact registry
docker push us-east4-docker.pkg.dev/rugged-night-193017/scheduled-jobs/med_audit:latest
