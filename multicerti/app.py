from multicerti import nginxparser
import shutil
import subprocess
from multicerti.to_tempfile import to_tempfile
from naval import ValidationError
import pprint
import sys

def cmd(*args, **kwargs):
    return subprocess.check_call(args, **kwargs)   
            
class App(object):

    def __init__(self, conf):
        try:
            self._conf = conf.validate()
        except ValidationError as exc:
            pprint.pprint(exc.error_details, stream = sys.stderr)
            sys.stderr.flush()
            sys.exit(1)
        
    def nginx_conf(self):
        vhosts = self._conf['vhosts']
        upstreams = ''.join(vhost.upstream_block() for vhost in vhosts)
        http_blocks = ''.join(vhost.http_server_block() for vhost in vhosts)
        https_blocks = ''.join(vhost.https_server_block() for vhost in vhosts)
        return nginxparser.dumps(
            nginxparser.loads(
                open(self._conf['nginx_conf_template']).read() % {
                    'upstreams': upstreams,
                    'servers': http_blocks + https_blocks
                }
            )
        )
            
    def _install_certificates(self):
        vhosts = self._conf['vhosts']
        ssl_vhosts = [
            vhost
            for vhost in vhosts
            if 'https' in vhost.protocols
        ]
        for vhost in ssl_vhosts:
            cmd('mkdir', '-p', vhost.letsencrypt_webroot())
            cmd('certbot', 'certonly', '--noninteractive', '--agree-tos', '--webroot',
                '--expand', # so that we're not asked if we want to expand
                '-m', vhost.registration_email,
                '-w', vhost.letsencrypt_webroot(),
                '-d', ','.join(vhost.domains)
            )
    
    def update_nginx_conf(self):
        temp_path = to_tempfile(self.nginx_conf(), prefix = self._conf['nginx_conf_location'] + ".")
        cmd(self._conf['nginx'], '-qt', '-c', temp_path) # check the conf before overwriting
        shutil.move(temp_path, self._conf['nginx_conf_location'])
        try:
            cmd(*self._conf['nginx_status'])
        except subprocess.CalledProcessError:
            cmd(*self._conf['nginx_start'])
        else:
            cmd(*self._conf['nginx_reload'])
            
    def update_certs(self):
        self.update_nginx_conf()
        self._install_certificates()
        self.update_nginx_conf()

