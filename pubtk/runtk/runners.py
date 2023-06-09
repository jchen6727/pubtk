import os
import subprocess
import json
import hashlib
from .utils import convert, set_map, create_script
from .template import sge_template


#TODO logger support
class dispatcher(object):
# dispatcher calls some runner python script
    #cmdstr = "python runner.py"
    #cmdstr = "mpiexec -n {} nrniv -python -mpi {}".format( 1, 'runner.py' )
    watch_file = None
    grepstr = 'PMAP'
    id = None
    env = {}
    def __init__(self, cmdstr=None, grepstr=None, env={}):
        if cmdstr:
            self.cmdstr = cmdstr
        if grepstr:
            self.grepstr = grepstr
        if env:
            self.env = env
        self.id = hashlib.md5(self.env.encode()).hexdigest()
        self.cmdarr = self.cmdstr.split()
        # need to copy environ or else cannot find necessary paths.
        self.__osenv = os.environ.copy()
        self.__osenv.update(env)

        if self.savekey:
            filevar = env[self.savekey].split('=')[-1].strip()
            self.filename = "{}".format(filevar)

    def get_command(self):
        return self.cmdstr

    def run(self):
        self.proc = subprocess.run(self.cmdarr, env=self.__osenv, text=True, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
        self.stdout = self.proc.stdout
        self.stderr = self.proc.stderr
        return self.stdout, self.stderr

    def shrun(self, template=sge_template, **kwargs):
        """
        instead of directly calling run, create and submit a shell script based on a custom template and 
        kwargs

        template: template of the script to be formatted
        kwargs: keyword arguments for template, must include unique {name}
            name: name for .sh, .run, .err files
        """
        self.env
        create_script(env=self.env, filename="{}.{}.sh".format(kwargs['name'], self.id), template=template, **kwargs)

        self.watch_file = subprocess.run()
        self.run()
        return self.stdout, self.stderr
    
    def check_run(self):
        # if file exists, return data, otherwise return None
         

class hpc_dispatcher(dispatcher):
# HPC using submission engine, currently written for SGE

    def __init__(self, cmdstr=None, env={}, watch_file=None):
        super().__init__(cmdstr=cmdstr, env=env)
        self.watch_file 
"""
    def gather_data(self):
        import json
        filename = "{}_data.json".format(self.filename)
        self.data = json.load( open(filename) )
        return self.data
"""

class runner(object):
    grepstr = 'PMAP' # unique delimiter to select environment variables to map
    # the datatype is can be defined before the grepstr
    # e.g. FLOATPMAP or STRINGPMAP
    _supports = { # Python > 3.6, dictionaries keep keys in order they were created, 'FLOAT' -> 'JSON' -> 'STRING'
        'FLOAT': float,
        'JSON': json.loads, #NB TODO? JSON is loaded in reverse order
        'STRING': staticmethod(lambda val: val),
    }
    mappings = {}# self.mappings keys are the variables to map, self.maps[key] are values supported by _supports
    debug = []# list of debug statements: self.debug.append(statement)
    def __init__(
        self,
        grepstr='PMAP',
        _testenv={}
    ):
        #self.debug.append("grepstr = {}".format(grepstr))
        self.grepstr = grepstr
        self.grepfunc = staticmethod(lambda key: grepstr in key )
        if not _testenv:
            self.greptups = {key: os.environ[key].split('=') for key in os.environ if
                             self.grepfunc(key)}
            self.debug.append(os.environ)
            # readability, greptups as the environment variables: (key,value) passed by 'PMAP' environment variables
            # saved the environment variables TODO JSON vs. STRING vs. FLOAT
        else: # supply _testenv dictionary for internal testing
            self.greptups = {key: _testenv[key].split('=') for key in _testenv if
                             self.grepfunc(key)}
        self.mappings = {
            val[0].strip(): self._convert(key.split(grepstr)[0], val[1].strip())
            for key, val in self.greptups.items()
        }

    def get_debug(self):
        return self.debug

    def get_mappings(self):
        return self.mappings


    def __getitem__(self, k):
        try:
            return object.__getattribute__(self, k)
        except:
            raise KeyError(k)

    def _convert(self, _type, val):
        return convert(self, _type, val)




class netpyne_runner(runner):
    """
    # runner for netpyne
    # see class runner
    mappings <-
    """
    sim = object()
    netParams = object()
    cfg = object()
    def __init__(self):
        super().__init__(grepstr='NETM')

    def set_mappings(self):
        for assign_path, value in self.mappings.items():
            set_map(self, assign_path, value)

    def create(self):
        self.sim.create(self.netParams, self.cfg)

    def simulate(self):
        self.sim.simulate()

    def save(self):
        self.sim.saveData()
