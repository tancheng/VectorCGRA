FROM ubuntu:22.04

RUN mkdir ${HOME}/cgra \
    && cd ${HOME}/cgra \
    && apt-get -y update \
    && apt-get -y install git \
    && apt-get -y install python3.10 \
    && apt-get -y install python3-pip \
    && apt-get -y install wget \
    && wget https://github.com/tancheng/pymtl-verilator/raw/master/verilator-travis-4.036.tar.gz \
    && tar -C ${HOME} -xzf verilator-travis-4.036.tar.gz \
    && rm -f ${HOME}/verilator-travis-4.036.tar.gz \
    && apt-get -y install graphviz \
    && apt-get -y install git libffi-dev \
    && apt-get -y install python3.10-venv \
    && python3 -m venv ${HOME}/venv \
    && pip install py==1.11.0 \
    && pip install wheel \
    && pip install -U git+https://github.com/tancheng/pymtl3.1@yo-struct-list-fix \
    && pip install hypothesis \
    && pip install pytest \
    && pip install py-markdown-table \
    && git clone https://github.com/tancheng/VectorCGRA.git \
    && cd VectorCGRA \
    && git submodule update --init \
    && mkdir -p build

ENV PATH="/root/verilator/bin:$PATH"
ENV VERILATOR_ROOT=/root/verilator
ENV PYMTL_VERILATOR_INCLUDE_DIR=/root/verilator/share/verilator/include

CMD ["tail", "-f", "/dev/null"]
