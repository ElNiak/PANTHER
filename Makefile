NPROC:=$(shell nproc)

# TODO for docker, more elegant
clean:
	docker kill $(docker ps -q)
	docker image prune -a

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

###################################################################################################
# BUILDER
###################################################################################################

# ----------------------------
# With Shadow
# ----------------------------

# IMPLEM="picoquic" make build-docker
build-docker:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t ubuntu-ivy -f Dockerfile.ubuntu .
	docker build -t ivy -f Dockerfile.ivy_1 .
	docker build -t shadow-ivy -f Dockerfile.shadow .
	docker build -t shadow-ivy-picotls -f Dockerfile.picotls --build-arg image=shadow-ivy .
	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy
build-docker-ivy:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# build-allinone-docker-ivy:
# 	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
# 	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
# 	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
# 	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy-short
build-docker-ivy-short:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy-gperf
build-docker-ivy-gperf:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build .
	docker build -t $(IMPLEM) -f Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build -t $(IMPLEM)-ivy -f Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .
	docker build -t $(IMPLEM)-ivy-gperf -f Dockerfile.gperf --build-arg image=$(IMPLEM) .

build-docker-compose:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build .
	IMPLEM="picoquic" make build-docker-ivy
	IMPLEM="quant" make build-docker-ivy
	make build-docker-visualizer
	make build-docker-ivy-standalone-short
	

# ----------------------------
# Standalone TODO
# ----------------------------


build-docker-visualizer:
	docker build -t ivy-visualizer -f Dockerfile.visualizer .

# TODO make lighter -> remove all ivy stuff only webserver
# make build-docker-ivy-standalone
build-docker-ivy-standalone:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t ubuntu-ivy -f Dockerfile.ubuntu .
	docker build -t ivy -f Dockerfile.ivy_1 .
	docker build -t ivy-picotls -f Dockerfile.picotls --build-arg image=ivy .
	docker build -t ivy-picotls-standalone -f Dockerfile.ivy_2 --build-arg image=ivy-picotls .

build-docker-ivy-standalone-short:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t ivy-picotls-standalone -f Dockerfile.ivy_2 --build-arg image=ivy-picotls .

# IMPLEM="picoquic" make build-docker-implem
build-docker-implem:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	docker build -t ubuntu-ivy -f Dockerfile.ubuntu .
	docker build -t ivy-picotls -f Dockerfile.picotls --build-arg image=ubuntu-ivy .
	docker build -t $(IMPLEM)-standalone -f Dockerfile.$(IMPLEM) --build-arg image=ivy-picotls .

build-all-docker-implem:
	IMPLEM="picoquic" make build-docker-implem
	IMPLEM="quant" make build-docker-implem
	IMPLEM="aioquic" make build-docker-implem
	IMPLEM="lsquic" make build-docker-implem

###################################################################################################
# RUNNER
###################################################################################################

# IMPLEM="picoquic" make launch-gui
launch-gui:
	xhost +local:docker
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/ivy_to_cpp.py:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/ivy_to_cpp.py \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -v /tmp/.X11-unix:/tmp/.X11-unix \
    		   -e DISPLAY=$(DISPLAY) \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --gui --compile  --initial_version 29 --alpn hq-29 --docker $(OPT)

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

# IMPLEM="picoquic" make launch-webapp
launch-webapp:
	#xhost +local:docker 			   #-v /tmp/.X11-unix:/tmp/.X11-unix \
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/ivy_to_cpp.py:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/ivy_to_cpp.py \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
    		   -e DISPLAY=$(DISPLAY) \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --webapp --compile  --initial_version 29 --alpn hq-29 --docker $(OPT)

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build


# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="" make test-draft29
test-draft29:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/ivy_to_cpp.py:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/ivy_to_cpp.py \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

# IMPLEM="picoquic" MODE="client" CATE="attacks_test" ITER="1" OPT="--vnet" make gperf-draft29
gperf-draft29:
	docker run --privileged --env GPERF=true --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy-gperf python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile --gperf --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build
	# pprof $(PWD)/QUIC-Ivy/doc/examples/quic /tmp/prof.out



# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="--vnet" make test-rfc9000
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="" make test-rfc9000
test-rfc9000:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 run_experiments.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop --docker $(OPT) || true

	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

change-permissions:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build

test-local-server-rfc9000:
	python3 run_experiments.py --mode server --categories global_tests --update_include_tls \
			   --timeout 180 --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop
test-local-client-rfc9000:
	python3 run_experiments.py --mode client --categories global_tests --update_include_tls \
			   --timeout 180 --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop

test-vnet:
	docker run --privileged -it picoquic-ivy ./setup_namespace.sh

launch-teams:
	docker build -t teams -f Dockerfile.teams  .
	xhost +local:docker
	docker run --privileged  -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$(DISPLAY) -it teams

compose:
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/test/temp
	sudo chown -R $(USER):$(USER) $(PWD)/QUIC-Ivy/doc/examples/quic/build .
	docker-compose up -d
	bash update_etc_hosts.sh  # TODO make copy before

# IMPLEM="picoquic" make start-bash
start-bash:
	docker run --privileged --cpus="$(NPROC).0" --memory="10g" --memory-reservation="9.5g" \
			   -v $(PWD)/tls-keys:/tmp/QUIC-FormalVerification/tls-keys \
			   -v $(PWD)/tickets:/tmp/QUIC-FormalVerification/tickets \
			   -v $(PWD)/qlogs:/tmp/QUIC-FormalVerification/qlogs \
			   -v $(PWD)/QUIC-Ivy/doc/examples/quic:/tmp/QUIC-FormalVerification/QUIC-Ivy/doc/examples/quic \
			   -v $(PWD)/QUIC-Ivy/ivy/include/1.7:/tmp/QUIC-FormalVerification/QUIC-Ivy/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy bash