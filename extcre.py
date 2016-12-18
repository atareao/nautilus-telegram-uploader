#!/usr/bin/env python3
import os
import shutil
import re
import subprocess
import shlex
import glob

KEY = '2962A198'
PPA = 'atareao/test'
PARENTDIR = os.path.abspath(os.path.dirname(__file__))
TEMPDIR = os.path.join(PARENTDIR, 'temporal')
FORGET = ['.git', '.gitignore', 'extcre.py', 'temporal']


def case_sensitive_replace(s, before, after):
    regex = re.compile(re.escape(before), re.I)
    return regex.sub(lambda x: ''.join(d.upper() if c.isupper() else d.lower()
                                       for c, d in zip(x.group(), after)), s)


def dow_dir(odirname, fb):
    for element in os.listdir(odirname):
        if os.path.basename(element) not in FORGET:
            element = os.path.join(odirname, element)
            if os.path.isfile(element):
                dow_file(element, fb)
            else:
                relative_path = os.path.relpath(element, PARENTDIR)
                ndirname = os.path.join(TEMPDIR, relative_path)
                if os.path.exists(ndirname):
                    shutil.rmtree(ndirname)
                os.mkdir(ndirname)
                dow_dir(element, fb)


def dow_file(ofilename, fb):
    relative_path = os.path.relpath(ofilename, PARENTDIR)
    nfilename = os.path.join(TEMPDIR, relative_path)
    head, tail = os.path.split(nfilename)
    tail = case_sensitive_replace(tail, 'nautilus', fb)
    nfilename = os.path.join(head, tail)
    if os.path.exists(nfilename):
        os.remove(nfilename)
    ofile = open(ofilename, 'r')
    odata = ofile.read()
    ofile.close()
    nfile = open(nfilename, 'w')
    ndata = case_sensitive_replace(odata, 'nautilus', fb)
    if fb == 'caja':
        ndata = ndata.replace("gi.require_version('Caja', '3.0')",
                              "gi.require_version('Caja', '2.0')")
    nfile.write(ndata)
    nfile.close()


def create_package(afolder):
    DEBIAN_DIR = os.path.join(afolder, 'debian')
    SRCDIR = os.path.join(afolder, 'src')
    CHANGELOG = os.path.join(afolder, 'debian', 'changelog')
    PYCACHEDIR = os.path.join(SRCDIR, '__pycache__')
    if os.path.exists(PYCACHEDIR):
        shutil.rmtree(PYCACHEDIR)
    changelogfile = open(CHANGELOG, 'r')
    data = changelogfile.readline()
    changelogfile.close()
    posi = data.find('(')
    posf = data.find(')')
    app = data[0:posi].lower().strip()
    version = data[posi+1:posf].strip()
    print('\r\n*** Building debian package... ***\r\n')
    p = subprocess.Popen(shlex.split('debuild -S -sa -k%s' % (KEY)),
                         stdout=subprocess.PIPE)
    p.communicate()
    # time.sleep(1)
    package = os.path.join(PARENTDIR, '%s_%s_source.changes' % (app, version))
    if os.path.exists(package):
        print('\r\n*** Uploading debian package ***\r\n')
        # os.system('dput ppa:"%s" "%s"' % (PPA, package))
        p = subprocess.Popen(shlex.split(
            'dput ppa:"%s" "%s"' % (PPA, package)),
            stdout=subprocess.PIPE)
        p.communicate()
        print('\r\n*** Uploaded debian package ***\r\n')
        print('\r\n*** Removing files ***\r\n')
        for afile in glob.glob(os.path.join(
                PARENTDIR, '%s_%s*' % (app, version))):
            os.remove(afile)
    else:
        print('\r\n*** Error: package not build ***')


if __name__ == '__main__':
    for fb in ['nautilus', 'nemo', 'caja']:
        print('\r\n*** Doing %s ***\r\n' % (fb.upper()))
        if os.path.exists(TEMPDIR):
            shutil.rmtree(TEMPDIR)
        os.makedirs(TEMPDIR)
        dow_dir(PARENTDIR, fb)
        os.chdir(TEMPDIR)
        # time.sleep(1)
        create_package(TEMPDIR)
    if os.path.exists(TEMPDIR):
        shutil.rmtree(TEMPDIR)
