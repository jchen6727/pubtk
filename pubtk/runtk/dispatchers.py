import os
import subprocess
import hashlib
from pubtk import runtk
from pubtk.runtk.submits import Submit
from pubtk.runtk.sockets import INETSocket, UNIXSocket
from pubtk.utils import create_path
import socket


def format_env(dictionary, value_type=None, index=0):
    """
    Parameters
    ----------
    dictionary - the dictionary of variable_path: values to add to the environment
    index (optional) - the index to start at for environment generation, defaults to 0
    value_type (optional) - forces the type of values added to the dictionary, how the runner interprets the values
                          - if not provided, the value_type will be based on the dictionary item's type per entry basis.
    use:
        format_env({'foo': 1, 'bar': 2.0, 'baz': 'three'})
    returns:
        {'INTRUNTK0': 'foo=1', 'FLOATRUNTK1': 'bar=2.0', 'STRRUNTK2': 'baz=three'}

    with runtk.GREPSTR being defined in as 'RUNTK' (see ./header.py)
    """
    cl = len(dictionary)
    get_type = staticmethod(lambda x: type(x).__name__)
    return {"{}{}{}".format(value_type or get_type(value).upper(), runtk.GREPSTR, cl + i):
                  "{}={}".format(key, value) for i, (key, value) in enumerate(dictionary.items())}

    # convert dictionary to proper elements
class Dispatcher(object):
    """
    base class for Dispatcher
    handles submitting the script to a Runner/Worker object and retrieving outputs

    initialized values:
    env ->
        dictionary of values to be exported to the simulation environment, can be within the subprocess call,
        or an environment script (some shell, env equivalent)
    grepstr ->
        the string value used in label generation (specifically the environment dictionary)
        defaults to runtk.GREPSTR ('RUNTK') (see ./header.py)
    gid ->
        an ID string that is unique to a Dispatcher <-> Runner pair. If it is not provided, it will be generated
        upon subprocess call by the environment dictionary and **kwargs
    """ 
    obj_count = 0 # persistent count N.B. may be shared between objects.

    def __init__(self, env=None, json=None, grepstr=runtk.GREPSTR, gid = None, **kwargs):
        """
        initializes base dispatcher class
        Parameters
        ----------
        env - any environmental variables to be passed to the subprocess
        grepstr - the string ID for subprocess to identify necessary environment variables
        gid - an ID string that is unique to the dispatcher <-> runner pair
        **kwargs are placed into a __dict__ item that can be accessed by __getattr__

        initializes gid, will set if the argument is supplied, otherwise the value will be
        created upon subprocess call.
        """

        #self.__dict__ = kwargs # the __dict__ has to come first or else env won't work...?
        #TODO what is the purpose of implementing a self.__dict__ in the FIRST place?
        self.env = env or {} # if env is None, then set to empty dictionary
        self.grepstr = grepstr
        self.gid = gid
        Dispatcher.obj_count = Dispatcher.obj_count + 1

    def add_json(self):
        pass
    def update_env(self, dictionary, value_type=None, format = True, **kwargs):
        """
        Parameters
        ----------
        dictionary - the dictionary of key: values to add to self.env
        value_type (optional) - the type of the values added in the dictionary, relevant if format is True (see
                                format_env() above)
        format (optional) - if True, the dictionary will be formatted by format_env() before being added to self.env

        Returns
        -------
        None

        the entries are added to the environment, either formatted (if format = True) or unformatted (if format = False):
        """
        if format:
            self.env.update(format_env(dictionary, value_type=value_type, index=len(self.env)))
        else:
            self.env.update(dictionary)

    def format_env(self, dictionary, value_type=None):
        """
        Parameters
        ----------
        dictionary - the dictionary of variable_path: values to add to the environment
        value_type - the type of the values added in the dictionary

        handles any global tasks prior to running the subprocess
            if self.gid = False, generates alphanumeric for self.gid based on self.env and **kwargs
        """
        cl = len(self.env)
        get_type = staticmethod(lambda x: type(x).__name__)
        return {"{}{}{}".format(value_type or get_type(value).upper(), self.grepstr, cl + i):
                      "{}={}".format(key, value) for i, (key, value) in enumerate(dictionary.items())}

        # convert dictionary to proper elements

    def init_run(self, **kwargs):
        """
        Parameters
        ----------
        **kwargs - of note, **kwargs here is used if necessary to help generate self.gid

        handles any global tasks prior to running the subprocess
            if self.gid = None, uses hashlib to generate alphanumeric for self.gid based on self.env and **kwargs then
            sets self.label = self.gid
            if self.gid already set, uses self.gid as self.label
        """
        if not self.gid:
            gstr = str(self.env) + str(kwargs)
            self.gid = hashlib.md5(gstr.encode()).hexdigest()
            self.label = "{}_{}".format(self.grepstr.lower(), self.gid)
        else:
            self.label = self.gid
        # convert dictionary to proper elements

    #def __getattr__(self, k):
    #TODO see self.__dict__ in init... not sure of this function utility
    #    # only called if __getattribute__ fails
    #    return self.__dict__[k]

    def save_env(self, filename):
        """
        Parameters
        ----------
        filename - filename to save json to

        saves the environment dictionary to a json file
        """
        import json
        with open(filename, 'w') as fptr:
            json.dump(self.env, fptr)
            fptr.close()



class SH_Dispatcher(Dispatcher):
    """
    Shell based Dispatcher that handles job generating shell script to submit jobs
    """
    def __init__(self, submit, project_path, output_path=".", **kwargs):
        """
        initializes dispatcher
        project_path: current working directory
        submit: Submit object (see pubtk.runk.submit)
        in **kwargs:
            gid: string to identify dispatcher by the created runner
            env: dictionary of environmental variables to be passed to the created runner
        """
        super().__init__(**kwargs)
        self.project_path = project_path
        self.output_path = create_path(project_path, output_path)
        self.submit = submit
        self.handles = None
        self.job_id = -1
        # create a "self.target" that contains the output_path and label?
        #self.label = self.gid

    def create_job(self, **kwargs):
        super().init_run()
        self.submit.create_job(label=self.label,
                               project_path=self.project_path,
                               output_path=self.output_path,
                               env=self.env,
                               **kwargs)
        self.handles = self.submit.get_handles()

    def submit_job(self):
        self.job_id = self.submit.submit_job()

    def run(self, **kwargs):
        self.create_job(**kwargs)
        self.job_id = self.submit.submit_job()

    def accept(self, **kwargs):
        pass


    def recv(self, **kwargs):
        pass

    def send(self, **kwargs):
        pass

    def clean(self, handles = None, **kwargs):
        if handles:
            for handle in handles:
                if os.path.exists(self.handles[handle]):
                    os.remove(self.handles[handle])


class SFS_Dispatcher(SH_Dispatcher):
    """
    This class can be improved by implementing a single file communication system without a signal file and checking
    proc.readline() -- see threading course

    what about grep for a specific run string?
    Shared File System Dispatcher utilizing file operations to submit jobs and collect results
    handles submitting the script to a Runner/Worker object
    """

    def create_job(self, **kwargs):
        super().create_job(**kwargs)

    def run(self, **kwargs):
        super().run(**kwargs)

    def get_run(self):
        # if file exists, return data, otherwise return False
        if os.path.exists(self.handles[runtk.SGLOUT]):
            with open(self.handles[runtk.MSGOUT], 'r') as fptr:
                data = fptr.read()
            return data # what if data itself is False equivalence
        return False

    def recv(self, **kwargs): # blocking function,
        data = False
        while not data:
            data = self.get_run()
        return data




class UNIX_Dispatcher(SH_Dispatcher):
    """
    AF UNIX Dispatcher utilizing sockets (requires socket forwarding)
    handles submitting the script to a Runner/Worker object
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.socket = None
        self.server = None

    def create_job(self, **kwargs):
        super().create_job()
        socket_name = "{}/{}.s".format(self.output_path, self.label)  # the socket file
        try:
            os.unlink(socket_name)
        except OSError as e:
            if os.path.exists(socket_name):
                raise OSError("issue when creating socket {}:".format(socket_name), e)
        self.socket = UNIXSocket(socket_name = socket_name)
        self.socket.listen()
        self.submit.create_job(label=self.label, project_path=self.project_path,
                               output_path=self.output_path, env=self.env, sockname=socket_name, **kwargs)
        self.handles = self.submit.get_handles()


    def run(self, **kwargs):
        self.create_job(**kwargs)
        self.job_id = self.submit.submit_job()

    def accept(self):
        """
        accept incoming connection from client
        this function is blocking
        """
        connection, peer_address = self.socket.accept()  # actual blocking statement
        return connection, peer_address

    def recv(self):
        """

        Returns
        -------

        """
        return self.socket.recv()

    def send(self, data):
        self.socket.send(data)
    def clean(self, handles=None):
        super().clean(handles)
        if self.socket:
            self.socket.close()

class INET_Dispatcher(SH_Dispatcher):
    """
    AF INET Dispatcher utilizing sockets
    handles submitting the script to a Runner/Worker object
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.socket = None

    def create_job(self, **kwargs):
        super().init_run(**kwargs)
        self.socket = INETSocket()
        socket_name = self.socket.listen() # one server <-> one client
        self.submit.create_job(label=self.label, project_path=self.project_path,
                               output_path=self.output_path, env=self.env, sockname=socket_name, **kwargs)
        self.handles = self.submit.get_handles()


    def submit_job(self):
        self.job_id = self.submit.submit_job()
    
    def run(self, **kwargs):
        self.create_job(**kwargs)
        self.job_id = self.submit.submit_job()

    def accept(self):
        """
        accept incoming connection from runner
        this function is blocking
        """
        connection, peer_address = self.socket.accept()  # actual blocking statement
        return connection, peer_address

    def recv(self):
        """

        Returns
        -------

        """
        return self.socket.recv()

    def send(self, data):
        self.socket.send(data)
    def clean(self, handles=None):
        super().clean(handles)
        if self.socket:
            self.socket.close()


class NOF_Dispatcher(Dispatcher):
    """
    No File Dispatcher, everything is run without generation of shell scripts.
    ? utility of NOF_Dispatcher vs. UNIX ?
    """
    def __init__(self, cmdstr='', env=None, **kwargs):
        """
        Parameters
        ----------
        initializes dispatcher
        cmdstr - command line call to be executed by the created runner (subprocess.run())
        env - any environmental variables to be inherited by the created runner
        """
        super().__init__(env=env, **kwargs)
        self.cmdstr = cmdstr
        self.env.update(os.environ.copy())

    def run(self):
        super().init_run()
        self.proc = subprocess.run(self.cmdstr.split(), env=self.env, text=True, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
        return self.proc