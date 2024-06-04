# :wrench: Installation 

Note, before implementation were added as submodule. Now we only consider Docker containers installation. (To be updated)



## :computer: Local Installation (Not Recommended)



See Dockerfile for dependencies and commands



## :whale: Single implementation 



```bash
# For a full installation including all dependencies and configurations:
IMPLEM="picoquic" make build-docker
```


## :whale: WebApp (Recommended) 

```bash
# For first installation 
make install

# For modification: 
# For major update in ivy:
make build-docker-compose-full
# For a minor update in some implementation:
make build-docker-compose
```

## :warning: Clean Up



```bash
# To clean Docker images and system:
make clean-docker-full
```




---
