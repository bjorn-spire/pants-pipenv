BUILD: Pipfile tmp/.container
	docker run -v $(shell pwd):/io pipenv-builder:latest /bin/bash -c "\
		PIPENV_INSTALL_TIMEOUT=1800 pipenv install --dev --keep-outdated \
		&& pipenv graph --json > Pipfile.lock.graph \
		&& sort_pipfile_lock_graph.py \
		&& pipenv_graph_to_build.py \
	"

tmp:
	@mkdir tmp

tmp/.container: tmp Dockerfile pipenv_graph_to_build.py sort_pipfile_lock_graph.py
	docker build -f Dockerfile -t pipenv-builder:latest . && \
		touch tmp/.container
