FROM fedora:39

LABEL Name=lab0
LABEL Version=1

ARG STUDENT=%ЛОГИН_СТУДЕНТА%
ENV STUDENT=$STUDENT



RUN dnf install --nodocs --setopt=install_weak_deps=False -y \
    sudo \
    util-linux \
    git \
    curl \
    vim \
    nano \
    python3 \
    python3-pip \
    python3-requests \
    procps \
    && pip3 install --no-cache-dir beautifulsoup4 \
    && rm -rf /var/cache /var/log/dnf* /var/log/yum.* \
    && dnf clean all


RUN groupadd -g 1000 $STUDENT \
    && useradd -ms /bin/bash -u 1000 -g $STUDENT $STUDENT


RUN echo "$STUDENT:$STUDENT" | chpasswd \
    && echo "$STUDENT ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$STUDENT


RUN echo "alias ll='ls -alF'" | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"
RUN echo "alias la='ls -A'" | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"
RUN echo "alias l='ls -CF'" | su $STUDENT -c "tee -a /home/$STUDENT/.bashrc"


USER $STUDENT


ENTRYPOINT ["/bin/bash"]
