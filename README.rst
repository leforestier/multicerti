.. role:: json(code)
   :language: json
   
.. role:: sh(code)
    :language: sh

My small python script to manage multiple domains served over http and/or https using *Let's encrypt* ssl certificates.
Multicerti configures nginx to act as a reverse http and https proxy server and deals automatically with the creation and renewal of ssl certificates using *certbot*.
The nginx configuration is generated using the *nginxparser* module from Fatih Erikli.

The script doesn't have a lot of options, but it provides a very quick way to deploy multiple sites on https.

----------------
Quick deployment
----------------

1. Requirements
===============

Nginx
-----  

Multicerti requires nginx. Install it using your favorite package manager, or download it from https://nginx.org/en/download.html .

If you've already been using nginx on your server and already have customized nginx's configuration, you should make a backup copy of your current ``nginx.conf``, because multicerti will overwrite it.

On FreeBSD, enable nginx in your ``rc.conf`` by running

.. code:: sh

    sysrc nginx_enable=YES

Python 3
--------

Python 3.3 or later is required. If you haven't already, install it using your favorite package manager.
Make sure to also have pip3 installed. Usually, you can install pip3 by running:

.. code:: sh

    python3 -m ensurepip
    
On Debian or Ubuntu, you'll probably need to install pip3 from the package manager.
You'll also need to get the python3-dev, libssl-dev and libffi-dev packages so that the python modules required by multicerti correctly install.

.. code:: sh

    apt-get install python3-pip python3-dev libssl-dev and libffi-dev


2. Install multicerti
=====================

Install 

.. code:: sh

    pip3 install multicerti
    
Then run

.. code:: sh

    multicerti reload
    
so that multicerti inspects your nginx installation and generates its default configuration files.

3. Edit the multicerti.conf file
================================

It's a json file. By default, its location is ``/usr/local/etc/multicerti/multicerti.conf``. Just add one or more virtual hosts to the `vhosts` list. Also add a `registration_email` key to the configuration file. This email is used when registering the ssl certificates with certbot.

.. code:: json

    {
        "vhosts": [
            {
                "domains": ["mysite.example.com"],
                "protocols": ["http", "https"],
                "backends": ["10.0.0.2:8080", "10.0.0.2:8081"],
                "http_to_https": true
            },
            {
                "domains": ["secure.example.com", "payment.example.com"],
                "protocols": ["https"],
                "backends": ["10.0.0.3:80"]
            },
            {
                "domains": ["oldsite.example.com"],
                "protocols": ["http", "https"],
                "redirect": "https://mysite.example.com"
            }
               
        ],
        "registration_email": "sysadmin@example.com"
    }

You can use the `".example.com"` string to add both the ``example.com`` and ``www.example.com`` domains to the list. You can also set a specific email address for a virtual host entry. For example:

.. code:: json

    {
        "vhosts": [
            {
                "domains": [".example.com"],
                "protocols": ["http", "https"],
                "backends": ["10.0.0.2:8080", "10.0.0.2:8081"],
                "registration_email": "bob@example.com",
                "http_to_https": true
            }  
        ],
        "registration_email": "sysadmin@example.com",
    }

This would register the ``example.com`` and ``www.example.com`` domains with the same ssl certificate, using ``bob@example.com`` as a  registration email address. The `http_to_https` option, as its name implies, redirects all http requests to https urls.

4. Run multicerti
=================

If you're using a server on which you had already customized your nginx installation, you should backup your ``nginx.conf``, because multicerti will overwrite it.

Now run, as root:

.. code:: sh

    multicerti reload

This is all you have to do. This will register and/or renew all your ssl certificates, and direct all your http and https traffic to the correct backends.

*Let's Encrypt* certificates issued by certbot have a validity of 90 days. Running :sh:`multicerti reload` as a monthly cron task will renew your certificates in due time. Pick a random day of the month and a random time of the day if you do that (not the first of the month at midnight). This is to avoid traffic peaks to the *Let's Encrypt*'s servers.


------------------------
Virtual hosts definition
------------------------

Each virtual host is defined as single json dictionnary that you add to the :json:`"vhosts"` entry of the ``multicerti.conf`` file.
Each virtual host definition must contain the following keys:

- :json:`"domains"`
    This is a list of domains.
    You can use the :json:`".example.com"` shortcut to add both the `www.example.com` and `example.com` domain.
    
    .. code:: json
        
        {
            "domains": [".example.com", "admin.example.com"],
            ...
        }

    
- :json:`"protocols"`
    A list of protocols. The only available protocols are :json:`"http"` or :json:`"https"`. You can supply one of them, or both.
    If you only supply :json:`"http"`, no ssl certificate will be issued for the domains of this virtual host.
    
    .. code:: json
        
        {
            "domains": [".example.com", "admin.example.com"],
            "protocols": ["http", "https"],
            ...
        }
        
Each virtual host must also contain exactly one of the following three keys:

- :json:`"backends"`
    A list of :json:`"ip:port"` strings. The http and/or https requests for the matching domains will be proxied to these adresses.
    
    .. code:: json
        
        {
            "domains": [".example.com", "admin.example.com"],
            "protocols": ["http", "https"],
            "backends": ["10.0.0.4:8080", "10.0.0.4:8081"]
        }
        
- :json:`"redirect"`
    A redirect url. For example:
    
    .. code:: json
        
        {
            "domains": ["old-site.example.com"],
            "protocols": ["http"],
            "redirect": "http://new-site.example.com"
        }
        
    A request for ``http://old-site.example.com/path/`` would receive a 301 http redirect to ``http://new-site.example.com/path/`` response.
    
- :json:`"root"`
    The path of a directory on the local machine. This is if you want to serve static content directly.
    
    .. code:: json
        
        {
            "domains": ["static.example.com"],
            "protocols": ["http", "https"],
            "root": "/var/www/static.example.com/"
        }
        
Each virtual host can also contain one of the following optional keys:

- :json:`"http_to_https"`
    This would redirect all the requests to ``http://domain.com/url`` to ``https://domain.com/url``
    
    .. code:: json
        
        {
            "domains": [".example.com", "admin.example.com"],
            "protocols": ["http", "https"],
            "backends": ["10.0.0.4:8080", "10.0.0.4:8081"],
            "http_to_https": true
        }
        
- :json:`"registration_email"`
    An e-mail address to use during the registration process with `letsencrypt`. You'll receive notices of certificate expirations at this address. If you don't supply a :json:`"registration_email"` in the virtual host configuration, the global :json:`"registration_email"` of the ``multicerti.conf`` will be used.
        
    
---------------
Multicerti.conf
---------------

The ``multicerti.conf`` file is located at ``/usr/local/etc/multicerti/multicerti.conf``.
If you want to use a different file, you can use the :sh:`-c` option:

.. code:: sh

    multicerti reload -c /my/directory/my_multicerti.conf
    
This json configuration file should contain the following keys:

- :json:`"vhosts"`
    A list of virtual hosts represented as dictionnaries, as described in the predeceding section
    
- :json:`"registration_email"`
    Unless you only use http and no https, you'll need to supply an e-mail address to use during the automated ssl certificate registration process.
    
The following keys are already created for you on the first run of multicerti. In most cases you don't need to change any of them.

- :json:`"nginx_status"`
    The command used to check if nginx is running. It should be something like :json:`["service", "nginx", "status"]` or :json:`["systemctl", "status", "nginx"]`. Note that it's a list, not a string.

- :json:`"nginx_start"`
    The command used to start nginx. It should be something like :json:`["service", "nginx", "start"]` or :json:`["systemctl", "start", "nginx"]`. Note that it's a list, not a string.

- :json:`"nginx_reload"`
    The command used to reload nginx configuration. It should be something like :json:`["service", "nginx", "reload"]` or :json:`["systemctl", "reload", "nginx"]`. Note that it's a list, not a string.

- :json:`"nginx"`
    The path of the nginx binary. If it's already on your PATH, you can just keep the default: :json:`"nginx"`. Otherwise maybe you'll want to specify the full path, for example :json:`"/usr/local/sbin/nginx"`.

- :json:`"nginx_conf_location"`
    The location of the ``nginx.conf`` file that should be overwritten by multicerti. Depending on your system, the initial configuration is set either to :json:`"/usr/local/etc/nginx/nginx.conf"` or to :json:`"/etc/nginx/nginx.conf"`.

- :json:`"nginx_conf_template"`
    The location of the template file used by multicerti to generate the ``nginx.conf`` file. The default is :json:`"/usr/local/etc/multicerti/nginx.conf.tpl"`. More on that in the next section.
  

-------------------------------------------
Customize the generated nginx configuration
-------------------------------------------

You can customize the ``nginx.conf`` that is generated by multicerti by editing the ``nginx.conf.tpl`` file (whose default location is ``/usr/local/etc/multicerti/nginx.conf.tpl`` ). It looks like a normal ``nginx.conf`` file, but it contains two placeholders: `%(upstreams)s` and `%(servers)s`. You can change everything else (number of nginx workers, logging options etc...).
Then regenerate `nginx.conf` using the command:

.. code:: sh

    multicerti reload --skip-certbot

The `--skip-certbot` option prevents multicerti from trying to create or renew ssl certificates. This is what you want if you're only changing the number of nginx workers or the location of the nginx log files for example.

-----------
GitHub repo
-----------

https://github.com/leforestier/multicerti
