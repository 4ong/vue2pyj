# -*- coding: utf-8 -*-
from gluon.custom_import import track_changes; track_changes(True)
import fs2json
import os
import socket
import copy
import gluon.fileutils


response.static_version = '0.0.4'
response.static_version_urls = True

http_host = request.env.http_host.split(':')[0]
remote_addr = request.env.remote_addr
try:
    hosts = (http_host, socket.gethostname(),
             socket.gethostbyname(http_host),
             '::1', '127.0.0.1', '::ffff:127.0.0.1')
except:
    hosts = (http_host, )

if request.is_https:
    session.secure()
elif (remote_addr not in hosts) and (remote_addr != "127.0.0.1"):
    raise HTTP(403,'Insecure channel')

session.forget()

def secure(f):
    def guard(*args, **kw):
        if gluon.fileutils.check_credentials(request):
            return f(*args, **kw)
        else:
            raise HTTP(403, 'not authorized')
    guard.x_name = f.__name__
    return guard


APPS_FOLDER = os.path.split(os.path.normpath(request.folder))[0]
API = dict()
def json_api(f):
    API[getattr(f, 'x_name', f.__name__)] = f
    return f


def index():
    if not gluon.fileutils.check_credentials(request):
        redirect(URL('admin', 'default', 'index',
                     vars = dict(send = URL('index')) )
        )
    response.delimiters = ('[[', ']]')
    response.view = 'index.html'
    return dict(web23py='web2py',
                title = 'Vue2pyj',
                static_version = response.static_version,
                app_root = '/'+request.application
    )

@json_api
def login(password = None, cb = None):
    if gluon.fileutils.check_credentials(request):
        return dict(user = True)
    if password:
        pwd = str(password) # may be unicode
        cb_url = URL('api', args = ['login'], vars = dict(cb='ok'))
        redirect(
            URL('admin', 'default', 'index',
                vars = dict(password = pwd, send = cb_url ))
        )
    elif cb == 'ok':
        return dict(user = True)

@json_api
@secure
def try_connect():
    return dict(message = 'ok')

@json_api
@secure
def logout():
    redirect(URL('admin', 'default', 'logout'))
    return dict(message = 'ok')


@json_api
@secure
def app_list():
    return dict(app_list = [app for app in next(os.walk(APPS_FOLDER))[1] \
                            if not app.startswith('__')] )


@json_api
def cm_themes():
    cm_themes_dir = os.path.join(request.folder, 'static/js/codemirror/theme')
    return [ fname for fname in os.listdir(cm_themes_dir) if fname.endswith('.css')]

@json_api
@secure
def get_fs(w23p_app = None):
    dir_list = {
        'controllers':'*',
        'static': {
            'js': {},
            'css': '*',
        },
        'modules':'*',
        'models':'*',
        'views':'*',
        'vuepy':'*',
    }
    app_folder = os.path.join(APPS_FOLDER, w23p_app) if w23p_app else os.path.normpath(request.folder)
    ret = fs2json.dir_to_fs(app_folder, dir_list)
    return ret

@json_api
@secure
def write_file(**fdata):
    w23p_app = fdata.get('w23p_app')
    app_folder = os.path.join(APPS_FOLDER, w23p_app)
    ret = fs2json.write_file(fdata, app_folder)
    return dict(ret)

@json_api
@secure
def del_file(fdata):
    w23p_app = fdata.get('w23p_app')
    app_folder = os.path.join(APPS_FOLDER, w23p_app)
    ret = fs2json.del_file(fdata, app_folder)
    return dict(ret)

@json_api
@secure
def compile_py(fp = None, w23p_app = None, code = None):
    fp = fp[0] == '/' and fp[1:] or fp
    fp = os.path.join(APPS_FOLDER, w23p_app, fp)
    if not os.path.isfile(fp):
        raise HTTP(404, web2py_error =  '`%s` not found' % fp)
    if not fp.endswith('.py'):
        raise HTTP(400, web2py_error = '`%s` is not python file' % fp)

    code_raw = (fs2json.PY2 and code.encode('utf8') or code) if code is not None else fs2json.safe_read(fp)
    code = code_raw.rstrip().replace('\r\n', '\n') + '\n'
    highlight = None
    import _ast
    error = None
    try:
        compile(code, fp, "exec", _ast.PyCF_ONLY_AST)
    except Exception as e:
        # offset calculation is only used for textarea (start/stop)
        start = sum([len(line) + 1 for l, line
                     in enumerate(code_raw.split("\n"))
                     if l < e.lineno - 1])
        if e.text and e.offset:
            offset = e.offset - (len(e.text) - len(
                e.text.splitlines()[-1]))
        else:
            offset = 0
        highlight = {'start': start, 'end': start +
                     offset + 1, 'lineno': e.lineno, 'offset': offset}
        try:
            ex_name = e.__class__.__name__
        except:
            ex_name = 'unknown exception!'
        error = dict(line = e.lineno, col = offset, message = ex_name)
    return dict(err = error )

def api():
    apif = API.get(request.args(0))
    if apif:
        return response.json(apif(*request.args[1:], **request.vars))
    raise HTTP(404)

