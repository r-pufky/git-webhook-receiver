# gitlab-webhook-receiver
Simple git webhook receiver.

## Source
The idea and base of the script is from these repos:

* Direct fork [pstauffer/gitlab-webhook-receiver](https://github.com/pstauffer/gitlab-webhook-receiver).
* Original fork [schickling/docker-hook](https://github.com/schickling/docker-hook).

## Configuration

### Git Secret Token
The script requires, that the git secret token is set! You can define the value
in the [configuration file](#example-config).

### Git Project Homepage
The structure of the [configuration file](#example-config) requires the homepage
of the gitlab project as key.

### Command
The command should be run after the hook was received.

### Example config
```
# file: config.yaml
---
# myrepo
https://git.example.ch/exmaple/myrepo:
  command: uname
  secret: mysecret-myrepo
  background: True
# test-repo
https://git.example.ch/exmaple/test-repo:
  command: uname
  secret: mysecret-test-repo
  background: True
```

## Script Arguments

### Port (-p, --port)
Define the listen port for the webserver. Default: **8666**

### Address (-a, --address)
Define the listen address for the webserver. Default: **0.0.0.0**

### Config (-c, --config)
Define the path to your configuration file. Default: **config.yaml**



## Run Script

```
python gitlab-webhook-receiver.py --port 8080 --config /etc/hook.yaml
```


### Help
```
usage: gitlab-webhook-receiver.py [-h] [-a ADDR] [-p PORT] [-c CFG]

Gitlab Webhook Receiver

optional arguments:
  -h, --help            show this help message and exit
  -a ADDR, --address ADDR
                        Address to listen on. (default: 0.0.0.0)
  -p PORT, --port PORT  Port to listen on. (default: 8666)
  -c CFG, --config CFG  Path to the config file. (default: None)
```