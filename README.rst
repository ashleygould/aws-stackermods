===============
AWS-stackermods
===============

A collection of stacker blueprint modules

-------------

Stacker is a python framework for deploying AWS cloudformation stacks.  A stacker
blueprint is a python module that builds a AWS cloudformation template using
troposphere.

For info on stacker and troposphere see:

- https://github.com/remind101/stacker
- http://stacker.readthedocs.io/en/latest/
- https://github.com/cloudtools/troposphere



Installing AWS-stackermods
--------------------------

Installing AWS-stackermods installs stacker, troposphere and all other requirements
for running stacker.

Stacker does not yet support python 3. Use python2.7 (too bad).

Clone this git repo into your homedir and install to ~/.local/ in editable mode::

  git clone https://github.com/ashleygould/aws-stackermods
  pip install --user -e aws-stackermods


I run it under a python2.7 virtualenv::

  mkdir ~/python-venv
  virtualenv -p /usr/bin/python2.7 ~/python-venv/python2.7
  source ~/python-venv/python2.7/bin/activate
  
  git clone https://github.com/ashleygould/aws-stackermods
  pip install -e aws-stackermods



Usage
-----

AWS-stackermods provides a utility script for getting info about it's blueprint
modules::

  # list blueprint modules in the collection
  stackermods -l

  # display help message for one of the modules
  stackermods vpc


Building the 'vpc' stack in 'example' namespace using sample config file::

  # just dump template to file
  mkdir -p /tmp/stack_templates/example-vpc/
  cd ~/path/to/aws-stackermods
  stacker build -i -r us-west-2 -d /tmp conf/vpc.conf.yml
  
  # build/update stack (interactive)
  stacker build -i -r us-west-2 conf/vpc.conf.yml
  
  # destroy stacks 
  stacker destroy -i -r us-west-2 conf/vpc.conf.yml
  # --force flag required to actually destroy stacks
  stacker destroy --force -r us-west-2 -f conf/vpc.conf.yml


For basic stacker usage::

  stacker -h
  stacker build -h




