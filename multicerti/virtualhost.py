import os.path
from multicerti import nginxparser
from threading import Lock


class VirtualHost(object):

    __last_id = 0
    __id_lock = Lock()
    
    ssl_ciphers = (
        'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:'
        'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
        'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:'
        'ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:'
        'ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:'
        'DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:'
        'ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:'
        'AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS'
    )   
    ssl_protocols = 'TLSv1 TLSv1.1 TLSv1.2'
    
    @classmethod
    def generate_id(cls):
        with cls.__id_lock:
            cls.__last_id += 1
            return cls.__last_id

    def __init__(self, domains, protocols = ('http',),
     http_to_https = False, backends = (), redirect = None, root = None, 
     registration_email = None
    ):
        assert bool(domains) and sum(map(bool, (root, backends, redirect))) == 1
        assert registration_email or not ('https' in protocols)
        self.domains = domains
        self.protocols = tuple(protocols)
        self.http_to_https = http_to_https
        self.backends = tuple(backends)
        self.redirect = redirect
        self.root = root
        self.registration_email = registration_email
        self.id = self.__class__.generate_id()
        
    def master_domain(self):
        for domain in self.domains:
            if os.path.exists(os.path.join('/etc/letsencrypt/live', domain, 'fullchain.pem')):
                return domain
        return self.domains[0]
    
    def fullchain_pem(self):
        return os.path.join('/etc/letsencrypt/live', self.master_domain(), 'fullchain.pem')
        
    def privkey_pem(self):
        return os.path.join('/etc/letsencrypt/live', self.master_domain(), 'privkey.pem')
        
    def letsencrypt_webroot(self):
        return os.path.join('/usr/local/www/letsencrypt', self.master_domain())
        
    def letsencrypt_exists(self):
        return os.path.exists(self.fullchain_pem())
        
    def upstream_block(self):
        if self.backends:
            return 'upstream frontends%s { %s }' % (
                self.id,
                ''.join(
                    ('server %s;' % backend) for backend in self.backends
                )
            )
        else:
            return ''
            
            
    def _location_content(self):
        if self.backends:
            return [
                ['proxy_pass_header', 'Server'],
                ['proxy_set_header', 'Host' ,'$http_host'],
                ['proxy_redirect', 'off'],
                ['proxy_set_header', 'X-Real-IP', '$remote_addr'],
                ['proxy_set_header', 'X-Scheme', '$scheme'],
                ['proxy_pass', 'http://frontends{id}'.format(id = self.id)]
            ]
        elif self.redirect:
            return [['return', '301 %s$request_uri' % self.redirect]]
        else:
            assert self.root
            return [['root', self.root]]
            
        
            
    def https_server_block(self):
        
        if 'https' in self.protocols and self.letsencrypt_exists():
            return nginxparser.dumps([[
                ['server'], [
                    ['listen', '443 ssl'],
                    ['server_name', ' '.join(self.domains)],
                    ['ssl_certificate', self.fullchain_pem()],
                    ['ssl_certificate_key', self.privkey_pem()],
                    ['ssl_session_cache', 'shared:SSL:1m'],
                    ['ssl_session_timeout',  '5m'],
                    ['ssl_protocols', self.ssl_protocols],
                    ['ssl_ciphers', self.ssl_ciphers],
                    ['ssl_prefer_server_ciphers',  'on'],
                    [ ['location', '/'], self._location_content() ]
                ]
            ]])
        else:
            return ''
            
    def http_server_block(self):
        http_block = [['listen', '80'], ['server_name', ' '.join(self.domains)]]
        if 'https' in self.protocols:
            http_block.append([
                ['location', '/.well-known/'], [ 
                    ['alias',  os.path.join(self.letsencrypt_webroot(), '.well-known/')],
                    ['autoindex', 'off']
                ]
            ])
        if 'http' in self.protocols:
            if self.http_to_https:
                http_block.append([
                    ['location', '/'], [
                        ['return', '301 https://$host$request_uri']
                    ]
                ])
            else:
                http_block.append([['location', '/'], self._location_content()])
        else:
            http_block.append([
                ['location', '/'], [
                    ['return', '404']
                ]
            ])

        return nginxparser.dumps([[['server'], http_block]])
        


