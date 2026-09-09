# BSD 3-Clause License
#
# Copyright 2022 Hewlett Packard Enterprise Development LP
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

FROM arti.dev.cray.com/baseos-docker-master-local/alpine:3.13 AS base

# Insert our emulator extentions
COPY src /app
COPY mockups/DL325 /app/api_emulator/redfish/static/DL325

RUN set -ex \
    && apk -U upgrade \
    && apk add \
        build-base \
        python3 \
        python3-dev \
        py3-pip \
        openssl \
        openssl-dev \
        libffi-dev \
        gcc \
        musl-dev \
        cargo \
        curl \
    && pip3 install --upgrade \
        pip \
        setuptools \
    && pip3 install wheel \
    && pip3 install -r /app/requirements.txt

EXPOSE 5000
ENV MOCKUPFOLDER="DL325"
ENV AUTH_CONFIG=""
ENV PORT=5000
ENV XNAME="x3000c0s0b0"
ENV MAC_SCHEMA=""
WORKDIR /app
ENTRYPOINT ["python3"]
CMD ["emulator.py"]