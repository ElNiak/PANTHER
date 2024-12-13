FROM panther_base_service_panther:latest

ENV DEBIAN_FRONTEND=noninteractive
# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}



# Install jq for JSON parsing
RUN apt-get install --fix-missing -y jq 

USER ${USER_N}

FROM ntap/quant:latest as quant

COPY --from=quant /bin/server /opt/quant/bin/server
COPY --from=quant /bin/client /opt/quant/bin/client


# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]