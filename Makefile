PROJECT_ID=your-gcp-project
REGION=asia-southeast1
REPO=apps
IMAGE=$(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/realestate-api:0.1.0

.PHONY: run build push gke
run:
	uvicorn main:app --reload --port 8000

build:
	docker build -t $(IMAGE) .

push:
	gcloud auth configure-docker $(REGION)-docker.pkg.dev
	docker push $(IMAGE)

e2e: build push