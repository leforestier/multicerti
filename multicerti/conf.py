from collections import OrderedDict
import datetime
import functools
import os, os.path
from multicerti import nginxparser
from multicerti.to_tempfile import to_tempfile
from multicerti.virtualhost import VirtualHost
from naval import *
import json
import shutil

class Conf(OrderedDict):

    DEFAULT_CONF_DIR = '/usr/local/etc/multicerti/'
    DEFAULT_CONF = 'multicerti.conf'
    DEFAULT_TEMPLATE = 'nginx.conf.tpl'
    DEFAULT_CONF_PATH = os.path.join(DEFAULT_CONF_DIR, DEFAULT_CONF)
    DEFAULT_TEMPLATE_PATH = os.path.join(DEFAULT_CONF_DIR, DEFAULT_TEMPLATE)

    @classmethod
    def default_conf(cls):

        if os.path.exists(cls.DEFAULT_CONF_PATH):
            conf = cls.load(cls.DEFAULT_CONF_PATH)
        else:
            conf = cls(vhosts = [])
            os.makedirs(cls.DEFAULT_CONF_DIR, exist_ok = True)
            
        if conf.add_good_defaults():
            conf.save(cls.DEFAULT_CONF_PATH)
            
        return conf
        
    @classmethod
    def load(cls, path):
        with open(path) as fp:
            conf_str = fp.read()
        dct = json.loads(conf_str, object_pairs_hook = OrderedDict)
        return cls(dct)
        
    def validate(self):
        return configuration_schema.validate(self)
        
    def save(self, path):
        temp_path = to_tempfile(json.dumps(self, indent = 4), prefix = path + '.')
        shutil.move(temp_path, path)
        
    def add_good_defaults(self):
        changes = 0
    
        try:
            system_nginx_conf = next(filter(
                os.path.exists,
                (
                    '/usr/local/etc/nginx/nginx.conf',
                    '/etc/nginx/nginx.conf'
                )
            ))
        except StopIteration:
            pass
        else:            
            if 'nginx_conf_location' not in self:
                self['nginx_conf_location'] = system_nginx_conf
                changes += 1
                
            if 'nginx_conf_template' not in self:
                self['nginx_conf_template'] = self.__class__.DEFAULT_TEMPLATE_PATH
                changes += 1
                
            if (
                self['nginx_conf_template'] == self.__class__.DEFAULT_TEMPLATE_PATH
                and
                not os.path.exists(self.__class__.DEFAULT_TEMPLATE_PATH)
            ):
                try:
                    with open(system_nginx_conf) as fp:
                        nginx_conf_str = fp.read()
                except (FileNotFoundError, OSError):
                    pass
                else:
                    temp_path = to_tempfile(
                        ''.join(self.__class__._make_template_out_of_nginx_conf(nginx_conf_str)),
                        prefix = self.__class__.DEFAULT_TEMPLATE_PATH + '.'
                    )
                    shutil.move(temp_path, self.__class__.DEFAULT_TEMPLATE_PATH)
            
        if 'nginx' not in self:
            self['nginx'] = 'nginx'
            changes += 1
            
        sysname = os.uname().sysname
        for command in ('status', 'start', 'reload'):
            key = 'nginx_%s' % command
            if key not in self:
                if sysname == 'Linux':
                    self[key] = ('systemctl', command, 'nginx')
                else:
                    self[key] = ('service', 'nginx', command)
                changes += 1
                
        return changes
    
    
    @classmethod
    def _make_template_out_of_nginx_conf(cls, nginx_conf_str):
    
        def filter_subitem(subitem):
            if subitem[0] in ('server_tokens', 'proxy_next_upstream'):
                return ''
            if subitem[0] == 'include':
                if 'sites-enabled' in subitem[1] or 'sites-available' in subitem[1]:
                    return ''
            if isinstance(subitem[0], list):
                if subitem[0][0] in ('server', 'upstream'):
                    return ''    
            return nginxparser.dumps([subitem])
            
        conf = nginxparser.loads(nginx_conf_str)
        for item in conf:
            if item[0] == ['http']:
                yield 'http {\n'
                for subitem in item[1]:
                    yield '    '
                    yield filter_subitem(subitem)
                    yield '\n'
                yield (
                    '    server_tokens off;\n'
                    '    proxy_next_upstream error;\n'
                    '    \n'
                    '    %(upstreams)s\n'
                    '    \n'
                    '    server {\n'
                    '        listen 80 default_server;\n'
                    '        server_name  _;\n'
                    '        location / {\n'
                    '            return 404;\n'
                    '        }\n'
                    '    }\n'
                    '    \n'
                    '    %(servers)s\n'
                    '    \n'
                    '}' )
                    
            else:
                yield nginxparser.dumps([item])
            yield '\n'
            
            
def expand_domain(domain):
    if domain.startswith('.'):
        return (domain[1:], 'www' + domain)
    else:
        return (domain,)

def vhost_schema(default_email = None):
    conditions = (
        [
            Assert(
                (lambda d: sum(int(key in  d) for key in ('backends', 'redirect', 'root')) == 1),
                error_message = "You must specify either a list of backends, a redirection url or a root directory." 
            )
        ],
        ['domains',
            Type(list),
            Each(expand_domain),
            (lambda lst: functools.reduce(tuple.__add__, lst, ())),
            Each(Domain),
            Save
        ],
        ['protocols',
            Type(list),
            Length(1,2),
            Each(("http", "https"))
        ],
        ['backends',
            Optional,
            Type(list),
            Length(min=1),
            Each(str)
        ],
        ['redirect',
            Optional,
            Url
        ],
        ['root',
            Optional,
            Type(str)
        ],
        ['http_to_https',
            Optional,
            Type(bool)
        ]
    )
    if default_email:
        conditions += (
            ['registration_email', Default(default_email), Email],
        )
    else:
        conditions += (
            ['registration_email', Optional, Email],
            [Assert(
                (lambda d: d.get('registration_email') or not ('https' in d['protocols'])),
                error_message = "You must specify a registration_email key to use the https protocol."
            )]
        )
    return Schema(*conditions)

configuration_schema = Schema(
    ['registration_email', Optional, Email],
    ['vhosts', Type(list)],
    [
        (lambda d: [
            vhost_schema(d.get('registration_email')).validate(vhost)
            for vhost in d['vhosts']
        ]),
        Each(lambda vhost: VirtualHost(**vhost)),
        SaveAs('vhosts')
    ],
    ['registration_email', Optional, Delete],
    ['nginx_conf_template',
        Type(str),
        Assert(os.path.exists, error_message = "The file does not exist.")
    ],
    ['nginx_conf_location',
        Type(str),
        Length(min=1)
    ],
    ['nginx_status',
        Default(('service', 'nginx', 'status')),
        Type(tuple, list),
        Each(str)
    ],
    ['nginx_start', 
        Default(('service', 'nginx', 'start')),
        Type(tuple, list),
        Each(str)
    ],
    ['nginx_reload', 
        Default(('service', 'nginx', 'reload')),
        Type(tuple, list),
        Each(str)
    ],
    ['nginx', Default('nginx'), Type(str)]
)



                 
