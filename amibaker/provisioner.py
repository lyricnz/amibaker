from fabric.api import env, settings, hide
from fabric.operations import run, put, sudo
from os import path


class Provisioner(object):
    PERMITTED_OPERATIONS = ['exec', 'copy']

    def __init__(self, ec2, **kwargs):
        self.__ec2 = ec2
        self.__quiet = kwargs.get('quiet', False)

    def provision(self, tasks):
        if self.__quiet:
            settings(hide('warnings', 'running', 'stdout', 'stderr'))

        # host to connect to
        env.host_string = self.__ec2.get_hostname()

        # ssh user to be used for this session
        env.user = self.__ec2.get_username()

        # no passwords available, use private key
        env.password = None

        # use ~/.ssh/config if available
        env.use_ssh_config = True

        # disconnect right after work is done
        env.eagerly_disconnect = True

        # no need to check fingerprint
        env.disable_known_hosts = True

        # TODO: Make this configurable through recipe YAML
        # number of ssh attempts
        env.connection_attempts = 10

        # TODO: Make this configurable through recipe YAML
        # how many seconds until considered failed attempt
        env.timeout = 30

        env.colorize_errors = True
        self.process_tasks(tasks)

    def process_tasks(self, tasks):
        for task in tasks:
            for operation, jobs in task.iteritems():
                assert operation in self.PERMITTED_OPERATIONS
                assert isinstance(jobs, list)  # TODO: support listifying attributes found at same level as operation

                for job in jobs:
                    getattr(self, '_{0}'.format(operation))(**job)

    def _exec(self, src=None, body=None, dest=None, cwd=None, args=None, use_sudo=True):
        assert src or body, "Must specify one of src (file to copy & execute) or body (inline script)"

        if src:
            assert path.isfile(src), "Cannot find source script '{0}'".format(src)

        if body:
            assert not args, "Cannot use arguments with embeded script, remove body and use src parameter instead."

        if args:
            assert isinstance(args, str), "Arguments must be a string, not {0}".format(type(args))

        if src and not dest:
            # TODO: come up with a temporary file!
            dest = run('mktemp')

        if src:
            self._copy(src=src, dest=dest, mode=0600)

        if dest:
            run_cmd = dest

            if args:
                run_cmd = '{0} {1}'.format(run_cmd, args)
        else:
            run_cmd = body

        if cwd:
            run_cmd = 'cd {0}; {1}'.format(cwd, run_cmd)

        saved_exception = None

        try:
            run(run_cmd)
        except Exception, e:
            saved_exception = e
        finally:
            run('rm {0}'.format(dest), warn_only=True)

        if saved_exception:
            raise saved_exception

    def _copy(self, src, dest, mode=0600):
        opts = {'use_sudo': True}

        dest_dir = path.dirname(dest)
        sudo("mkdir -p %s" % dest_dir)

        if mode:
            opts['mode'] = mode

        put(src, dest, **opts)
