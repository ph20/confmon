# -*- mode: ruby -*-
# vi: set ft=ruby :

ENV['VAGRANT_DEFAULT_PROVIDER'] = 'docker'
DEFAULTDIR = File.dirname(__FILE__)
WORKSPACE = File.expand_path('./', __FILE__)
EXPOSEDPORT = 33023

Vagrant.configure("2") do |config|
  config.vm.define "devbox"
  config.ssh.username = "cisco"
  config.vm.boot_timeout = 10
  config.vm.hostname = "devbox"
  config.ssh.port = EXPOSEDPORT
  config.ssh.host = "127.0.0.1"


  config.vm.provider "docker" do |d|
    d.build_dir = "."
    d.build_args = ["-t=local/confmon_asa_system_test:2019.02.04"]
    d.name = "confmon_asa_system_test"
    d.has_ssh = true
    d.ports = ["#{EXPOSEDPORT}:22"]

    d.vagrant_machine = "dockerhost"
    d.force_host_vm = true
    d.vagrant_vagrantfile = "/home/ogrynch/ASA/wipro/devenv/docker-host-vm/Vagrantfile"
  end
  config.vm.synced_folder "./", "/workspace"
  config.vm.synced_folder ".", "/vagrant", disabled: true
end