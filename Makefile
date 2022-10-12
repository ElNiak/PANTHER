NPROC:=$(shell nproc)

# TODO for docker, more elegant
clean:
	echo "TODO"
	# TODO

install:
	git submodule update --init --recursive 
	git submodule update --recursive
	cd QUIC-Ivy;
	git submodule update --init --recursive 
	git submodule update --recursive
	git checkout rfc-9000
	mkdir doc/examples/quic/build; mkdir doc/examples/quic/test/temp
	cd submodules/picotls/
	git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76

# IMPLEM="picoquic" make build-docker
build-docker:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t ivy -f Dockerfile.ivy_1 .
	docker build -t shadow-ivy -f Dockerfile.shadow .
	docker build -t shadow-ivy-picotls -f Dockerfile.picotls .
	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy
build-docker-ivy:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy-gperf
build-docker-ivy-gperf:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

	# docker build -t ivy -f Dockerfile.ivy_1 .
	# docker build -t shadow-ivy -f Dockerfile.shadow .
	# docker build -t shadow-ivy-picotls -f Dockerfile.picotls .

	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .
	docker build -t $(IMPLEM)-ivy-gperf -f Dockerfile.gperf --build-arg image=$(IMPLEM) .


# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="" make test-draft29
test-draft29:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/ivy_to_cpp.py:/QUIC-FormalVerification/QUIC-Ivy/ivy/ivy_to_cpp.py \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

# IMPLEM="picoquic" MODE="client" CATE="attacks_test" ITER="1" OPT="--vnet" make gperf-draft29
gperf-draft29:
	docker run --privileged --env GPERF=true --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy-gperf python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile --gperf --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	# pprof $(PWD)/QUIC-Ivy/doc/examples/quic /tmp/prof.out



# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="--vnet" make test-rfc9000
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="" make test-rfc9000
test-rfc9000:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

change-permissions:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build


test-vnet:
	docker run --privileged -it picoquic-ivy ./setup_namespace.sh

# IMPLEM="picoquic" make start-bash
start-bash:
	docker run --privileged --cpus="$(NPROC).0" --memory="10g" --memory-reservation="9.5g" \
			   -v $(PWD)/tls-keys:/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy bash