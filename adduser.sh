#!/bin/bash
# Vagrant-specific configuration
USER_PASSWORD=$(/usr/bin/openssl passwd -quiet  -crypt 'cisco')
SUDOUSERS_FILE=/etc/sudoers.d/10_cisco
USER_NAME=$1
USERADD_ARGS=""
if [ ! -z "$2" ]
then
      USERADD_ARGS="--uid $2"
fi
echo "[+] Adding user ${USER_NAME} => ${USERADD_ARGS}"
/usr/sbin/useradd --password ${USER_PASSWORD} --comment 'Vagrant User' --create-home ${USERADD_ARGS} --user-group ${USER_NAME}
if [ ! -f ${SUDOUSERS_FILE} ]; then
    echo 'Defaults env_keep += "SSH_AUTH_SOCK"' > ${SUDOUSERS_FILE}
fi
echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >> ${SUDOUSERS_FILE}
/bin/chmod 0440 ${SUDOUSERS_FILE}
/usr/bin/install --directory --owner=${USER_NAME} --group=${USER_NAME} --mode=0700 "/home/${USER_NAME}/.ssh"
/usr/bin/curl -s --output "/home/${USER_NAME}/.ssh/authorized_keys" --location https://raw.github.com/mitchellh/vagrant/master/keys/vagrant.pub
/bin/chown ${USER_NAME}:${USER_NAME} "/home/${USER_NAME}/.ssh/authorized_keys"
/bin/chmod 0600 "/home/${USER_NAME}/.ssh/authorized_keys"
