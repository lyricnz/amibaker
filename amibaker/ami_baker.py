import yaml
import time
from jinja2 import Template
from .ami_ec2 import AmiEc2
from provisioner import Provisioner


class AmiBaker:
    def __init__(self, recipe, **kwargs):
        self.__recipe = yaml.load(recipe)
        self.__render_tags()
        self.__quiet = kwargs.get('quiet', False)
        self.__keep_instance = kwargs.get('keep_instance', False)

    def __render_tags(self):
        def render(tags, **kwargs):
            for key, value in tags.iteritems():
                template = Template(value)
                tags[key] = template.render(**kwargs)

        if not self.__recipe['ami_tags']['Name']:
            self.__recipe['ami_tags']['Name'] = 'amibaker - {{ timestamp }}'

        if not self.__recipe['ec2_tags']['Name']:
            self.__recipe['ec2_tags']['Name'] = \
                self.__recipe['ami_tags']['Name']

        timestamp = int(time.time())

        render(self.__recipe['ec2_tags'], timestamp=timestamp)
        render(self.__recipe['ami_tags'], timestamp=timestamp)

    def bake(self):
        ec2 = AmiEc2(quiet=self.__quiet, recipe=self.__recipe)
        ec2.instantiate()

        provisioner = Provisioner(ec2, quiet=self.__quiet)
        provisioner.provision(self.__recipe['provisioning_script'])

        image_id = ec2.create_image()

        if not self.__keep_instance:
            ec2.wait_until_image_available()
            ec2.terminate()

        print 'Your AMI has been cooked and is ready to be consumed: ' + \
            image_id
