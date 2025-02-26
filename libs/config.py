import os
import sys
import json
import inspect
import traceback
import configparser

__version__='1.2'

class InvalidValue(Exception):
    pass

class Section():
    def __init__(self, name, comment):
        self.name = name
        self.comment = comment
        self.field_dict = {}

    def add_field(self, key, field, overwrite=False):
        if not key in self.field_dict.keys() or overwrite:
            self.field_dict[key] = field
        else:
            print(f'Error: A field named {key} already exists in section {self.name}')
            sys.exit()

    
    def get_field_list(self):
        return self.field_dict.values()

class Field():
    def __init__(self, required=True, default=None, allowed=[], comment=None, commented=True):
        self.required = required
        self.default = default
        self.allowed = allowed
        self.comment = comment
        self.commented = commented
  
    def parse(self, key, value, config):
        return value

class TextField(Field):
    def __init__(self, required=True, default=None, allowed=[], lower=False, upper=False, strip=True, lstrip=False, rstrip=True, comment=None, commented=True):
        super().__init__(required=required, default=default, allowed=allowed, comment=comment, commented=commented)
        self.lower = lower
        self.upper = upper
        self.strip = strip
        self.lstrip = lstrip
        self.rstrip = rstrip

    def parse(self, key, value, config):
        if value is None:
            return value
        if self.lower:
            value = value.lower()
        if self.upper:
            value = value.upper()
        if self.lstrip:
            value = value.lstrip()
        if self.rstrip:
            value = value.rstrip()
        if self.strip:
            value = value.strip()
        return value

class IntegerField(Field):
    def __init__(self, required=True, default=None, allowed=[], min=None, max=None, comment=None, commented=True):
        super().__init__(required=required, default=default, allowed=allowed, comment=comment, commented=commented)
        self.min = min
        self.max = max

    def parse(self, key, value, config):
        try:
            res = int(value)
            return res
        except ValueError as e:
            raise InvalidValue(e) from None
        if self.min is not None and res < self.min:
            raise InvalidValue()
        if self.max is not None and res > self.max:
            raise InvalidValue()

class BooleanField(Field):
    def __init__(self, required=True, default=None, allowed=[], comment=None, commented=True):
        super().__init__(required=required, default=default, allowed=allowed, comment=comment, commented=commented)

    def parse(self, key, value, config):
        return str(value).strip().lower() in ['true', 'yes', 'ok', 'o', 'y', 't', '1']

class ListField(Field):
    def __init__(self, required=True, default=None, allowed=[], model=None, separator=',', comment=None, commented=True, **kargs,):
        super().__init__(required=required, default=default, allowed=allowed, comment=comment, commented=commented)
        self.model = model
        self.separator = separator
        self.kargs = kargs

    def parse(self, key, value, config):
        res = []
        if value is not None and type(value) is str:
            res = value.split(self.separator)
        if self.model is not None:
            process_res = []
            for entry in res:
                field = self.model(**self.kargs)
                try:
                    process_res.append(field.parse(key, entry, config))
                except InvalidValue:
                    print(f'Invalid value "{entry}" in ListField {self.section}.{key}: {value}')
                    raise InvalidValue() from None
            return process_res
        else:
            return res

class PathField(Field):
    def __init__(self, required=True, default=None, allowed=[], root=None, mkdir=False, comment=None, commented=True):
        super().__init__(required=required, default=default, allowed=allowed, comment=comment, commented=commented)
        self.root = root
        self.mkdir = mkdir

    def parse(self, key, value, config):
        if self.root is None:
            self.root = config.PROJECT_DIR
        
        res = value
        if os.name == 'nt':
            if not (res.startswith('.') or res.startswith('\\\\') or (len(res) >= 2 and res[1:2] == ':')):
                res = os.path.join(self.root, res)
        elif os.name == 'posix':
            if not (res.startswith('.') or res.startswith('/')):
                res = os.path.join(self.root, res)   
        
        if self.mkdir:
            if not os.path.exists(res):
                os.mkdir(res)
        return res

class Config():
    def __init__(self, definition=None, comment=None, default_config_path=[], dict=None):
        self.CONFIG = None
        if not 'DEFAULT_CONFIG_PATH' in dir(self) or len(default_config_path) > 0:
            self.DEFAULT_CONFIG_PATH = default_config_path
        if not 'comment' in dir(self):
            self.comment = comment
        self.section_dict = {}
        self.config_path = None

        if definition is None:
            for attr_name in dir(self):
                attr = getattr(self, attr_name)
                if inspect.isclass(attr) and not attr_name.startswith('_'):
                    section_name = attr_name.lower()
                    section_comment = None
                    field_dict = {}
                    for sub_attr_name, sub_attr in attr.__dict__.items():
                        if sub_attr_name == '__section__':
                            section_name = sub_attr
                        if sub_attr_name == '__comment__':
                            section_comment = sub_attr
                        if issubclass(sub_attr.__class__, Field):
                            field_dict[sub_attr_name.lower()] = sub_attr
                    self.add_section(section_name, comment=section_comment, field_dict=field_dict)
        else:
            if '__comment__' in dir(definition):
                self.comment = definition.__comment__
            for attr_name, attr in definition.__dict__.items():
                if inspect.isclass(attr) and not attr_name.startswith('_'):
                    section_name = attr_name.lower()
                    section_comment = None
                    field_dict = {}
                    for sub_attr_name, sub_attr in attr.__dict__.items():
                        if sub_attr_name == '__section__':
                            section_name = sub_attr
                        if sub_attr_name == '__comment__':
                            section_comment = sub_attr
                        if issubclass(sub_attr.__class__, Field):
                            field_dict[sub_attr_name.lower()] = sub_attr
                    self.add_section(section_name, comment=section_comment, field_dict=field_dict)
        
    def add_section(self, name, comment=None, field_dict={}, overwrite=False):
        section = self.section_dict.get(name)
        if section is None:
            section = Section(name, comment=comment)
            self.section_dict[name] = section
        else:
            if section.comment is None or (comment is not None and overwrite):
                section.comment = comment
            elif comment is not None and comment != section.comment:
                print(f'Warning: A section named {name} already exists with a different comment')
        for key, field in field_dict.items():
            section.add_field(key, field, overwrite=overwrite)
        return section
    
    def merge(self, config, overwrite=False):
        if not type(config) is self.__class__:
            config = self.__class__(definition=config)

        if self.comment is None or (config.comment is not None and overwrite):
            self.comment = config.comment
        else:
            print(f'Warning: Config already has its own comment')
        for section_name, section in config.section_dict.items():
            self.add_section(section_name, comment=section.comment, field_dict=section.field_dict, overwrite=overwrite)
     
    def parse_field(self, section_name, key, field):
        section = self.CONFIG.get(section_name)
        if section is None:
            if field.default is not None:
                print(f'Warning: Could not find field {section_name}.{key} because section {section_name} is missing. Using default value {field.default}')
                self.CONFIG[section_name] = {}
                self.CONFIG[section_name][key] = field.default
                section = self.CONFIG.get(section_name)
            elif not field.required:
                raise Exception(f'Config section is missing: {section_name}')
        
        value = section.get(key)
        if value is None or (type(value) is str and value.strip() == ''):
            if not field.required:
                value = None
            elif field.default is not None:
                value = field.default
            else:
                raise Exception(f'Key {key} not found in section {section_name}')

        if value is None:
            self.CONFIG[section_name][key] = value
        else:
            try:
                parsed_value = field.parse(key, value, self)
                allowed_value_list = []
                if type(field.allowed) is str:
                    pass
                    if '.' in field.allowed:
                        allowed_value_list = self.get(field.allowed.split('.')[0], '.'.join(field.allowed.split('.')[1:]))
                    else:
                        allowed_value_list = self.get(section_name, field.allowed)
                    if not type(allowed_value_list) is list:
                        print(allowed_value_list)
                        raise Exception(f'Error while parsing field {section_name}.{key}: allowed values pointer {field.allowed} doesn\'t exist or isn\'t a ListField object') from None
                elif type(field.allowed) is list:
                    allowed_value_list = field.allowed
                if len(allowed_value_list) > 0 and not parsed_value in allowed_value_list:
                    raise InvalidValue()
            except InvalidValue:
                if field.default is not None:
                    print(f'Warning: Invalid value {value} for key {key} in section {section_name}. Using default value {field.default}')
                    parsed_value = field.default
                else:
                    raise Exception(f'Invalid value {value} for {section_name}.{key}') from None
                
            self.CONFIG[section_name][key] = parsed_value

    def populate(self, config_path_list=None, reload=False):
        if type(config_path_list) is str:
            config_path_list = [config_path_list]
        elif config_path_list is None or len(config_path_list) == 0:
            config_path_list = self.DEFAULT_CONFIG_PATH
        
        if config_path_list is None or len(config_path_list) == 0:
            return False
        if self.CONFIG is not None and not reload:
            return False

        self.CONFIG = {}

        config_reader = configparser.ConfigParser()
        processed_config_path_list = config_reader.read(config_path_list)
        if len(processed_config_path_list) == 0:
            raise Exception('No config available at the following location:\n{}'.format('\n'.join(config_path_list)))
        else:
            self.config_path = processed_config_path_list[0]
        for section in config_reader.sections():
            self.CONFIG[section] = {}
            for key, value in config_reader[section].items():
                self.CONFIG[section][key] = value

        for section in self.section_dict.values():
            for key, field in section.field_dict.items():
                try:
                    self.parse_field(section.name, key, field)
                except Exception as e:
                    print(f'Error while parsing configuration field {section.name}.{key} in {self.config_path}')
                    traceback.print_exc()
                    sys.exit()

        return True

    def __getitem__(self, uri):
        self.populate()
        if '.' in uri:
            section = uri.split('.')[0]
            key = '.'.join(uri.split('.')[1:])
            return self.get(section, key)
        else:
            return self.get(uri)
    
    def get(self, section, key=None, default=None):
        self.populate()
        section = section.lower().strip()
        if self.CONFIG is None:
            raise Exception('Configuration has not been initialized')
        if key is None:
            return self.CONFIG.get(section, {})
        else:
            key = key.lower().strip()
            return self.CONFIG.get(section, {}).get(key, default)

    def sections(self):
        self.populate()
        if self.CONFIG is None:
            return []
        else:
            return self.CONFIG.keys()
        
    def print_template(self):
        res = ''
        if self.comment is not None:
            for line in self.comment.split('\n'):
                res = f'{res}# {line}\n'

        for section_name, section in self.section_dict.items():
            res = f'{res}\n'
            if section.comment is not None:
                for line in section.comment.split('\n'):
                    res = f'{res}# {line}\n'
            res = f'{res}[{section_name}]\n'
            
            for key, field in section.field_dict.items():
                if field.comment is not None:
                    for line in field.comment.split('\n'):
                        res = f'{res}# {line}\n'
                if field.allowed is not None:
                    if type(field.allowed) is list and len(field.allowed) > 0:
                        res = f'{res}# {key}={"|".join(field.allowed)}\n'
                    elif type(field.allowed) is str:
                        res = f'{res}# {key}=value from {field.allowed}\n'
                entry = ''
                if not field.required and field.commented:
                    entry = '# '
                entry = f'{entry}{key}='

                if field.default is not None:
                    if type(field) is ListField and field.default==[]:
                        field.default=''
                    entry = f'{entry}{field.default}'
                res = f'{res}{entry}\n'

        res = res.strip()

        print(res)
        return res

    def dump(self):
        self.populate()
        if self.CONFIG is not None:
            return json.dumps(self.CONFIG, indent=4)
    
    def print(self):
        self.populate()
        if self.CONFIG is not None:
            print(self.dump())
        else:
            print('Config not intialized')