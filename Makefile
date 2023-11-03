NPROC:=$(shell nproc)

# TODO for docker, more elegant
clean:
	#docker kill $(docker ps -q)
	docker image prune -a

clean-docker:
	docker image prune
	docker image prune -a
	docker rmi $(docker images -a -q) 
	#  docker system prune -a -f

install:
	git submodule update --init --recursive 
	git submodule update --recursive
	cd src/QUIC-Ivy-Attacker;git submodule update --init --recursive 
	cd src/QUIC-Ivy-Attacker;git submodule update --recursive
	# git checkout rfc-9000
	# git checkout master
	cd src/QUIC-Ivy-Attacker;mkdir doc/examples/quic/build; mkdir doc/examples/quic/test/temp; 
	cd src/QUIC-Ivy-Attacker;mkdir -p protocol-testing/quic/build; mkdir -p protocol-testing/quic/test/temp; touch protocol-testing/quic/test/temp/data.csv
	cd src/QUIC-Ivy-Attacker;mkdir -p protocol-testing/bgp/build; mkdir -p protocol-testing/bgp/test/temp; touch protocol-testing/bgp/test/temp/data.csv
	cd src/QUIC-Ivy-Attacker;mkdir -p protocol-testing/minip/build; mkdir -p protocol-testing/minip/test/temp; touch protocol-testing/minip/test/temp/data.csv
	make checkout-git
	make build-docker-compose-full


checkout-git:
	cd src/QUIC-Ivy-Attacker/submodules/picotls/;git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76
	cd src/implementations/quic-implementations/aioquic/;git checkout d272be10b93b09b75325b139090007dae16b9f16
	cd src/implementations/quic-implementations/boringssl/; git checkout a9670a8b476470e6f874fef3554e8059683e1413; git submodule init; git submodule update
	cd src/implementations/quic-implementations/lsquic/; git checkout 0a4f8953dc92dd3085e48ed90f293f052cff8427; 
	cd src/implementations/quic-implementations/picoquic/; git checkout bb67995f2d7c0e577c2c8788313c3b580d3df9a7; 
	cd src/implementations/quic-implementations/quant/; git checkout 9e309c05f79fb6aa3889dcf7df60b550249d2a2a;  git submodule update --init --recursive
	cd src/implementations/quic-implementations/picoquic/; git checkout bb67995f2d7c0e577c2c8788313c3b580d3df9a7; 
	cd src/implementations/quic-implementations/picotls/; git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76; 

###################################################################################################
# BUILDER
###################################################################################################

# ----------------------------
# With Shadow
# ----------------------------

# IMPLEM="picoquic" make build-docker
build-docker:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
	docker build --rm -t ubuntu-ivy -f src/containers/Dockerfile.ubuntu .
	# [+] Building 1046.5s (19/19) FINISHED                                                                                                                                           
	docker build --rm -t ivy -f src/containers/Dockerfile.ivy_1 .
	docker build --rm -t shadow-ivy -f src/containers/Dockerfile.shadow .
	docker build --rm -t shadow-ivy-picotls -f src/containers/Dockerfile.picotls --build-arg image=shadow-ivy .
	docker build --rm -t $(IMPLEM) -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy
build-docker-ivy:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
	docker build --rm -t $(IMPLEM) -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .


# IMPLEM="picoquic" make build-docker-ivy-short
build-docker-ivy-short:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
	docker build --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .

# IMPLEM="picoquic" make build-docker-ivy-gperf
build-docker-ivy-gperf:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	docker build --rm -t $(IMPLEM) -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=shadow-ivy-picotls .
	docker build --rm -t $(IMPLEM)-ivy -f src/containers/Dockerfile.ivy_2 --build-arg image=$(IMPLEM) .
	docker build --rm -t $(IMPLEM)-ivy-gperf -f src/containers/Dockerfile.gperf --build-arg image=$(IMPLEM) .

build-docker-compose:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	# QUIC
	IMPLEM="picoquic-shadow" make build-docker-ivy
	# IMPLEM="picoquic-no-retransmission-shadow" make build-docker-ivy
	# IMPLEM="picoquic-old-shadow" make build-docker-ivy
	# IMPLEM="picoquic" make build-docker-ivy
	# IMPLEM="picoquic-shadow-bad" make build-docker-ivy
	# IMPLEM="quant" make build-docker-ivy
	# MiniP
	IMPLEM="ping-pong" make build-docker-ivy
	# IMPLEM="ping-pong-flaky" make build-docker-ivy
	# IMPLEM="ping-pong-fail" make build-docker-ivy
	# BGP
	# IMPLEM="gobgp" make build-docker-ivy
	IMPLEM="bird" make build-docker-ivy
	# QUIC tools
	# make build-docker-visualizer
	make build-docker-ivy-standalone

build-docker-compose-full:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	IMPLEM="picoquic-shadow" make build-docker
	# IMPLEM="picoquic-old-shadow" make build-docker-ivy
	# IMPLEM="picoquic-shadow-bad" make build-docker-ivy
	# IMPLEM="picoquic-no-retransmission-shadow" make build-docker-ivy
	IMPLEM="picoquic" make build-docker-ivy
	# IMPLEM="quant" make build-docker-ivy
	IMPLEM="ping-pong" make build-docker-ivy
	# IMPLEM="ping-pong-flaky" make build-docker-ivy
	# IMPLEM="ping-pong-fail" make build-docker-ivy
	# make build-docker-visualizer
	make build-docker-ivy-standalone-short
	

# ----------------------------
# Standalone TODO
# ----------------------------


build-docker-visualizer:
	docker build --rm -t ivy-visualizer -f src/containers/Dockerfile.visualizer .

# TODO make lighter -> remove all ivy stuff only webserver
# make build-docker-ivy-standalone
build-docker-ivy-standalone:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	docker build --rm -t ubuntu-ivy -f src/containers/Dockerfile.ubuntu .
	docker build --rm -t ivy -f src/containers/Dockerfile.ivy_1 .
	docker build --rm -t ivy-picotls -f src/containers/Dockerfile.picotls --build-arg image=ivy .
	docker build --rm -t ivy-picotls-standalone -f src/containers/Dockerfile.ivy_2 --build-arg image=ivy-picotls .

build-docker-ivy-standalone-short:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
	docker build --rm -t ivy-picotls-standalone -f src/containers/Dockerfile.ivy_2 --build-arg image=ivy-picotls .

# IMPLEM="picoquic" make build-docker-implem
build-docker-implem:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	docker build --rm -t ubuntu-ivy -f src/containers/Dockerfile.ubuntu .
	docker build --rm -t ivy-picotls -f src/containers/Dockerfile.picotls --build-arg image=ubuntu-ivy .
	docker build --rm -t $(IMPLEM)-standalone -f src/containers/Dockerfile.$(IMPLEM) --build-arg image=ivy-picotls .

build-all-docker-implem:
	IMPLEM="picoquic" make build-docker-implem
	IMPLEM="quant" make build-docker-implem
	IMPLEM="aioquic" make build-docker-implem
	IMPLEM="lsquic" make build-docker-implem

###################################################################################################
# RUNNER
###################################################################################################

# IMPLEM="picoquic" make launch-webapp
launch-webapp:
	#xhost +local:docker 			   #-v /tmp/.X11-unix:/tmp/.X11-unix \
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/PFV/tls-keys \
			   -v $(PWD)/tickets:/PFV/tickets \
			   -v $(PWD)/qlogs:/PFV/qlogs \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic:/PFV/QUIC-Ivy-Attacker/doc/examples/quic \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/ivy_to_cpp.py:/PFV/QUIC-Ivy-Attacker/ivy/ivy_to_cpp.py \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/include/1.7:/PFV/QUIC-Ivy-Attacker/ivy/include/1.7 \
    		   -e DISPLAY=$(DISPLAY) \
			   -it $(IMPLEM)-ivy python3 pfv.py --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --webapp --compile  --initial_version 29 --alpn hq-29 --docker $(OPT)

	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	


# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="" make test-draft29
test-draft29:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/PFV/tls-keys \
			   -v $(PWD)/tickets:/PFV/tickets \
			   -v $(PWD)/qlogs:/PFV/qlogs \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic:/PFV/QUIC-Ivy-Attacker/doc/examples/quic \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/ivy_to_cpp.py:/PFV/QUIC-Ivy-Attacker/ivy/ivy_to_cpp.py \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/ivy_tracer.py:/PFV/QUIC-Ivy-Attacker/ivy/ivy_tracer.py \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/ivy_compiler.py:/PFV/QUIC-Ivy-Attacker/ivy/ivy_compiler.py \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/include/1.7:/PFV/QUIC-Ivy-Attacker/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 pfv.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	

# IMPLEM="picoquic" MODE="client" CATE="attacks_test" ITER="1" OPT="--vnet" make gperf-draft29
gperf-draft29:
	docker run --privileged --env GPERF=true --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/PFV/tls-keys \
			   -v $(PWD)/tickets:/PFV/tickets \
			   -v $(PWD)/qlogs:/PFV/qlogs \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic:/PFV/QUIC-Ivy-Attacker/doc/examples/quic \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/include/1.7:/PFV/QUIC-Ivy-Attacker/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy-gperf python3 pfv.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile --gperf --initial_version 29 --alpn hq-29 --docker $(OPT) || true

	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
	# pprof $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic /tmp/prof.out



# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="--vnet" make test-rfc9000
# IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="3" OPT="" make test-rfc9000
test-rfc9000:
	docker run --privileged --cpus="$(NPROC).0" \
			   -v $(PWD)/tls-keys:/PFV/tls-keys \
			   -v $(PWD)/tickets:/PFV/tickets \
			   -v $(PWD)/qlogs:/PFV/qlogs \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic:/PFV/QUIC-Ivy-Attacker/doc/examples/quic \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/include/1.7:/PFV/QUIC-Ivy-Attacker/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy python3 pfv.py --mode $(MODE) --categories $(CATE) --update_include_tls \
			   --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop --docker $(OPT) || true

	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	

change-permissions:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/

test-local-server-rfc9000:
	python3 pfv.py --mode server --categories global_tests --update_include_tls \
			   --timeout 180 --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop
test-local-client-rfc9000:
	python3 pfv.py --mode client --categories global_tests --update_include_tls \
			   --timeout 180 --iter $(ITER) --compile  --initial_version 1 --alpn hq-interop

test-vnet:
	docker run --privileged -it picoQUIC-Ivy-Attacker ./setup_namespace.sh

launch-teams:
	docker build --rm -t teams -f src/containers/Dockerfile.teams  .
	xhost +local:docker
	docker run --privileged  -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$(DISPLAY) -it teams

permissions:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	
# https://jtreminio.com/blog/running-docker-containers-as-current-host-user/
compose:
	sudo chown -R $(USER):$(GROUPS) $(PWD)/src/QUIC-Ivy-Attacker/
	xhost +
	docker-compose up -d
	cd src/pfv/scripts/hosts/; bash update_etc_hosts.sh  # TODO make copy before

# IMPLEM="picoquic" make start-bash
start-bash:
	docker run --privileged --cpus="$(NPROC).0" --memory="10g" --memory-reservation="9.5g" \
			   -v $(PWD)/tls-keys:/PFV/tls-keys \
			   -v $(PWD)/tickets:/PFV/tickets \
			   -v $(PWD)/qlogs:/PFV/qlogs \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/doc/examples/quic:/PFV/QUIC-Ivy-Attacker/doc/examples/quic \
			   -v $(PWD)/src/QUIC-Ivy-Attacker/ivy/include/1.7:/PFV/QUIC-Ivy-Attacker/ivy/include/1.7 \
			   -it $(IMPLEM)-ivy bash