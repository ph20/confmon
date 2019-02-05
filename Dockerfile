# docker build
FROM kick-bxb-cent2.cisco.com:5000/pyats-3.1_test
RUN yum -y -q update
RUN yum -y -q install --setopt=protected_multilib=false tk-devel zlib-devel bzip2 bzip2-devel readline-devel sqlite \
	sqlite-devel gcc glibc-devel.i686 openssl.i686 libffi-devel.i686 libX11.i686 \
	readline.i686 libgcc.i686 zlib.i686 libffi-devel libffi libffi-devel.i686 libffi.i686 openssl-devel \
	vim sshpass mlocate
RUN /kick/bin/pip install ipython
ADD adduser.sh /root/adduser.sh
RUN /bin/chmod +x /root/adduser.sh && /root/adduser.sh cisco 1000
ADD requirements.txt /root/requirements.txt
RUN /kick/bin/pip install -r /root/requirements.txt
WORKDIR /workspace
